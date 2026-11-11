"""Self-hosted Office conversion and searchable PDF OCR helpers."""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

import fitz

MAX_INPUT = 100 * 1024 * 1024
MAX_PAGES = 300
MAX_RENDER_PIXELS = 20_000_000
OFFICE_EXTS = {".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp"}


def _safe_stem(name):
    stem = Path(name or "document").stem
    stem = re.sub(r"[^\w.-]+", "_", stem, flags=re.UNICODE).strip("._")
    return (stem or "document")[:80]


def _office2pdf(files):
    if len(files) != 1:
        raise ValueError("Convert one Office file at a time")
    name, raw = files[0]
    ext = Path(name or "").suffix.lower()
    if ext not in OFFICE_EXTS:
        raise ValueError("Supported formats: DOC, DOCX, ODT, RTF, XLS, XLSX, ODS, PPT, PPTX, ODP")
    if len(raw) > MAX_INPUT:
        raise ValueError("File exceeds the 100 MB limit")
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if not lo:
        raise ValueError("LibreOffice is not installed")
    with tempfile.TemporaryDirectory(prefix="sygpdf-office-") as td:
        root = Path(td)
        source = root / ("input" + ext)
        source.write_bytes(raw)
        outdir = root / "out"
        outdir.mkdir()
        profile = root / "lo-profile"
        # Each invocation gets a private profile, disables first-run/update prompts,
        # and has no access to any other user's LibreOffice process/profile.
        env = dict(os.environ)
        env.update({"HOME": str(root), "SAL_USE_VCLPLUGIN": "svp"})
        cmd = [lo, "-env:UserInstallation=" + profile.as_uri(), "--headless", "--nologo",
               "--nodefault", "--nolockcheck", "--norestore", "--convert-to", "pdf",
               "--outdir", str(outdir), str(source)]
        # The parent worker restricts Internet sockets before starting the converter.
        result = subprocess.run(cmd, cwd=root, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=80)
        target = outdir / "input.pdf"
        if result.returncode != 0 or not target.is_file():
            detail = result.stderr.decode("utf-8", "replace")[-500:]
            raise ValueError("Office conversion failed" + (f": {detail}" if detail else ""))
        data = target.read_bytes()
        if len(data) > 200 * 1024 * 1024:
            raise ValueError("Converted PDF exceeds the 200 MB limit")
        try:
            pdf = fitz.open(stream=data, filetype="pdf")
            if pdf.page_count > MAX_PAGES:
                raise ValueError("Converted PDF exceeds the 300 page limit")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError("LibreOffice produced an invalid PDF") from e
        return _safe_stem(name) + ".pdf", data


def _ocr(files, opts):
    if len(files) != 1:
        raise ValueError("OCR one PDF at a time")
    name, raw = files[0]
    if len(raw) > MAX_INPUT:
        raise ValueError("File exceeds the 100 MB limit")
    lang_choice = str(opts.get("language", opts.get("lang", "eng"))).lower().replace(" ", "")
    langs = {"english": "eng", "eng": "eng", "malay": "msa", "msa": "msa", "eng+msa": "eng+msa", "english+malay": "eng+msa", "malay+english": "eng+msa"}
    lang = langs.get(lang_choice)
    if not lang:
        raise ValueError("Choose English, Malay, or English + Malay")
    tesseract = shutil.which("tesseract")
    if not tesseract:
        raise ValueError("Tesseract OCR is not installed")
    try:
        src = fitz.open(stream=raw, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open {name or 'PDF'}: {e}") from e
    if src.needs_pass:
        raise ValueError("PDF is password protected; unlock it first")
    if not 1 <= src.page_count <= MAX_PAGES:
        raise ValueError("OCR supports PDFs with 1 to 300 pages")
    dpi = max(72, min(300, int(opts.get("dpi", 180))))
    out = fitz.open()
    with tempfile.TemporaryDirectory(prefix="sygpdf-ocr-") as td:
        for i, page in enumerate(src):
            rect = page.rect
            scale = dpi / 72
            if rect.width * rect.height * scale * scale > MAX_RENDER_PIXELS:
                scale *= (MAX_RENDER_PIXELS / (rect.width * rect.height * scale * scale)) ** 0.5
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = Path(td) / f"page-{i}.png"
            pix.save(str(image))
            try:
                proc = subprocess.run([tesseract, str(image), "stdout", "-l", lang, "tsv"],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90,
                                      check=False, env={**os.environ, "OMP_THREAD_LIMIT": "2"})
            except subprocess.TimeoutExpired as e:
                raise ValueError(f"OCR timed out on page {i + 1}") from e
            if proc.returncode:
                msg = proc.stderr.decode("utf-8", "replace")[-350:]
                raise ValueError("Tesseract failed; check that the selected language data is installed" + (f": {msg}" if msg else ""))
            new = out.new_page(width=rect.width, height=rect.height)
            new.insert_image(new.rect, filename=str(image))
            # TSV coordinates refer to the rendered page. Add an invisible text
            # layer so the page stays visually identical and searchable/selectable.
            sx, sy = rect.width / pix.width, rect.height / pix.height
            for line in proc.stdout.decode("utf-8", "replace").splitlines()[1:]:
                cols = line.split("\t", 11)
                if len(cols) < 12 or not cols[11].strip():
                    continue
                try:
                    x, y, w, h = map(float, cols[6:10])
                except ValueError:
                    continue
                text = cols[11].strip()
                # Invisible render mode (3); anchor near each word's baseline.
                pt = fitz.Point(max(0, x * sx), min(rect.height, (y + h) * sy))
                size = max(4, min(48, h * sy * 0.8))
                new.insert_text(pt, text, fontsize=size, fontname="helv", render_mode=3,
                                overlay=True)
    return _safe_stem(name) + "_searchable.pdf", out.tobytes(garbage=3, deflate=True)


def process(tool: str, files: list[tuple[str, bytes]], opts: dict):
    """Run office2pdf or OCR; return (download_name, PDF bytes)."""
    tool = str(tool).lower().replace("-", "").replace("_", "")
    opts = opts or {}
    if not files:
        raise ValueError("Upload at least one file")
    if tool in ("office2pdf", "officetopdf"):
        return _office2pdf(files)
    if tool in ("ocr", "searchableocr", "pdftosearchable"):
        return _ocr(files, opts)
    raise ValueError(f"Unsupported advanced tool: {tool}")
