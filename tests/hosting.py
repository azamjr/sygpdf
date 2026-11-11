"""Check the actual app entry points behind an HTTPS hosting URL."""
import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aiohttp.test_utils import TestClient, TestServer
import app

async def main():
    os.environ["RENDER_EXTERNAL_URL"] = "https://sygpdf-test.example"
    async with TestClient(TestServer(app.create_app())) as client:
        headers = {"Host": "sygpdf-test.example"}
        health = await client.get("/healthz", headers=headers)
        assert health.status == 200
        assert len((await health.json())["tools"]) == 13
        home = await client.get("/", headers=headers)
        assert home.status == 200
        assert "office2pdf" in await home.text()
        asset = await client.get("/assets/local.js", headers=headers)
        assert asset.status == 200
        assert (await client.get("/",headers={"Host":"attacker.example"})).status == 403
        rejected = await client.post("/api/process",
            headers={**headers,"Origin":"https://attacker.example"})
        assert rejected.status == 403
        assert rejected.headers.get("Cache-Control") == "no-store"
        allowed = await client.post("/api/process",
            headers={**headers,"Origin":"https://sygpdf-test.example"})
        assert allowed.status == 400  # It passes origin validation, then needs files.
        print("HTTPS origin, health, UI, asset and rejection checks passed")
asyncio.run(main())
