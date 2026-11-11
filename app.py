"""PDF workspace for local use or an HTTPS container host."""
import asyncio
import json
import os
import pickle
import sys
import signal
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from aiohttp import web

ROOT = Path(__file__).resolve().parent
LIMIT = 32 * 1024 * 1024
TOOLS = set("merge split organize rotate compress protect unlock watermark number pdf2jpg img2pdf office2pdf ocr".split())


@web.middleware
async def privacy(request, handler):
    try:
        port = os.getenv("PORT", "8765")
        hosts = {"127.0.0.1:" + port, "localhost:" + port}
        origins = set()
        public_url = os.getenv("SYGPDF_PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL")
        if public_url:
            url = urlsplit(public_url)
            if url.scheme != "https" or not url.netloc or url.path not in {"", "/"}:
                raise web.HTTPServiceUnavailable(text="Invalid public URL configuration.")
            hosts.add(url.netloc)
            origins.add("https://" + url.netloc)
        if request.host not in hosts:
            raise web.HTTPForbidden()
        origins.add("http://" + request.host)
        # Use the configured public HTTPS URL, never an untrusted forwarded header.
        origin = request.headers.get("Origin")
        if request.method == "POST" and origin and origin not in origins:
            raise web.HTTPForbidden()
        response = await handler(request)
    except web.HTTPException as exc:
        response = exc
    response.headers.update({
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'",
    })
    return response


async def health(request):
    return web.json_response({"status": "ok", "tools": sorted(TOOLS)})


async def index(request):
    return web.FileResponse(ROOT / "static/index.html")


async def process(request):
    if request.content_type != "multipart/form-data":
        raise web.HTTPBadRequest(text="Select files using the tool form.")
    if request.app["slot"].locked():
        raise web.HTTPServiceUnavailable(text="A job is running. Try again shortly.")
    async with request.app["slot"]:
        files, fields, total = [], {}, 0
        try:
            reader = await request.multipart()
            async for part in reader:
                if part.name not in {"files", "opts", "tool"} or len(files) >= 100 and part.name == "files":
                    raise ValueError("Invalid form or too many files.")
                data = bytearray()
                while chunk := await part.read_chunk():
                    total += len(chunk)
                    if total > LIMIT:
                        raise ValueError("Select up to 32 MiB per job.")
                    data.extend(chunk)
                if part.name == "files":
                    files.append((Path(part.filename or "input").name, bytes(data)))
                else:
                    fields[part.name] = data.decode()
            tool = fields.get("tool")
            opts = json.loads(fields.get("opts", "{}"))
            if tool not in TOOLS or not isinstance(opts, dict) or not files:
                raise ValueError("Select a tool and at least one file.")
        except (ValueError, AssertionError, KeyError) as exc:
            return web.json_response({"error": str(exc)}, status=400)
        scratch = tempfile.TemporaryDirectory(prefix="sygpdf-")
        # Converters receive no hosting credentials or application secrets.
        worker_env = {key: os.environ[key] for key in (
            "PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH", "TESSDATA_PREFIX",
            "SYSTEMROOT", "PYTHONPATH"
        ) if key in os.environ}
        worker_env.update({"TMPDIR": scratch.name, "HOME": scratch.name,
                           "PYTHONDONTWRITEBYTECODE": "1"})
        worker = await asyncio.create_subprocess_exec(sys.executable, str(ROOT / "worker.py"),
            start_new_session=True, env=worker_env, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            output, _ = await asyncio.wait_for(worker.communicate(pickle.dumps((tool, files, opts))), timeout=90)
        except asyncio.TimeoutError:
            return web.json_response({"error":"Job exceeded 90 seconds. Try fewer pages."}, status=422)
        finally:
            try:
                os.killpg(worker.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await worker.wait()
            scratch.cleanup()
        if worker.returncode or not output.startswith(b"OK\n"):
            msg = output[4:].decode(errors="replace")[:250] if output.startswith(b"ERR\n") else "Processing failed or exceeded the worker limit."
            return web.json_response({"error":msg}, status=422)
        _, name, body = output.split(b"\n", 2)
        from urllib.parse import quote
        filename = name.decode()
        return web.Response(body=body, content_type="application/octet-stream", headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + quote(filename,safe="")})


def create_app():
    app = web.Application(middlewares=[privacy], client_max_size=LIMIT)
    app["slot"] = asyncio.Semaphore(1)
    app.add_routes([web.get("/", index), web.post("/api/process", process), web.get("/healthz", health)])
    app.router.add_static('/assets/', ROOT / 'static/assets')
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=os.getenv("SYGPDF_BIND", "127.0.0.1"),
                port=int(os.getenv("PORT", "8765")), access_log=None)
