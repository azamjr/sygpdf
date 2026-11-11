"""Functional smoke check with synthetic documents, exercised over HTTP."""
import asyncio
import os
import io
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fitz
from aiohttp import FormData, web
from aiohttp.test_utils import TestClient, TestServer
import app


async def main():
    site = web.Application(middlewares=[app.privacy])
    site['slot'] = asyncio.Semaphore(1)
    site.router.add_post('/api/process', app.process)
    source = fitz.open()
    for label in ('FIRST PAGE', 'SECOND PAGE'):
        source.new_page().insert_text((60, 100), label, fontsize=30)
    pdf = ('input.pdf', source.tobytes())
    image = ('page.png', source[0].get_pixmap().tobytes('png'))
    async with TestClient(TestServer(site)) as client:
        async def run(tool, files, **options):
            import json
            data = FormData()
            data.add_field('tool', tool)
            data.add_field('opts', json.dumps(options))
            for name, content in files:
                data.add_field('files', content, filename=name)
            response = await client.post('/api/process', data=data, headers={'Host': os.getenv('SYGPDF_TEST_HOST', 'localhost:8765'),
                        **({'Origin': os.environ['SYGPDF_TEST_ORIGIN']} if 'SYGPDF_TEST_ORIGIN' in os.environ else {})})
            result = await response.read()
            assert response.status == 200, (tool, result[:240])
            print(tool, response.status)
            return result
        def doc(data):
            return fitz.open(stream=data, filetype='pdf')
        assert len(doc(await run('merge',[pdf,pdf]))) == 4
        with zipfile.ZipFile(io.BytesIO(await run('split',[pdf]))) as z:
            assert len(z.namelist()) == 2 and len(doc(z.read(z.namelist()[1]))) == 1
        assert 'SECOND' in doc(await run('organize',[pdf], pages='2,1'))[0].get_text()
        assert doc(await run('rotate',[pdf],degrees=90))[0].rotation == 90
        assert 'FIRST' in doc(await run('compress',[pdf]))[0].get_text()
        locked = await run('protect',[pdf],password='sample')
        assert doc(locked).needs_pass
        assert 'FIRST' in doc(await run('unlock',[('locked.pdf',locked)],password='sample'))[0].get_text()
        assert 'DRAFT' in doc(await run('watermark',[pdf],text='DRAFT'))[1].get_text()
        assert '8' in doc(await run('number',[pdf],start=7))[1].get_text()
        assert (await run('pdf2jpg',[pdf],pages='1')).startswith(b'\xff\xd8')
        scan = await run('img2pdf',[image])
        assert doc(scan)[0].get_images()
        assert 'FIRST' in doc(await run('ocr',[('scan.pdf',scan)]))[0].get_text().upper()
        office = ('document.rtf', br'{\rtf1\ansi Example office text}')
        assert 'Example office text' in doc(await run('office2pdf',[office]))[0].get_text()
asyncio.run(main())
