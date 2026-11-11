# sygpdf
A PDF toolbox for Ubuntu or a Docker web service. Merge, organize and rotate run in the browser. Other tools use the computer serving this application. The interface and assets are bundled. Jobs run one at a time in short-lived processes. PDF jobs pass through memory. Office conversion and OCR also use private temporary directories, removed when the job finishes. The app keeps no job history. Downloads remain wherever you save them. OS swap and browser download history follow your machine's settings.

## Run with Docker Compose
From this directory, run `docker compose up --build` and open http://127.0.0.1:8765 . Stop with Ctrl+C. Internet access is needed to acquire the image and dependencies on the first build.

## Run directly on Ubuntu
Install Python 3.12+ and venv. For Office conversion and OCR on Ubuntu, also install the native engines:

`sudo apt install libreoffice-writer libreoffice-calc libreoffice-impress tesseract-ocr-eng tesseract-ocr-msa libseccomp2`

Then run:
```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```
Open http://127.0.0.1:8765 . Keep the terminal open while using the tools. This configuration is for use on your own computer. Each host worker job accepts at most 32 MiB of input and runs for up to 90 seconds.

## Scope
The first release handles page organization, compression, password protection and removal with a known password, stamps, page numbers and image conversions. Compression savings depend on the input. Editing a digitally signed file can invalidate its signatures. Office-to-PDF supports Word, Excel and PowerPoint files. Searchable PDF uses Tesseract to rasterize pages and add selectable text. Keep the original for forms, digital signatures and vector artwork. Permanent redaction, PDF/A, editable PDF-to-Office conversion, HTML conversion, repair and signing workflows are future work. PyMuPDF uses AGPL/commercial licensing; review its terms before redistributing or offering a hosted service.

## GitHub Pages
Under Settings → Pages select Deploy from a branch, main, /docs. The Pages version runs Merge, Organize and Rotate in the browser. The download on that page contains the full 13-tool application for local processing.

## Full online service
The Docker image serves all 13 tools and the web interface from one origin, including
LibreOffice conversion and Tesseract OCR in English and Bahasa Melayu.
The render.yaml blueprint selects a free service for initial deployment, with no
persistent disk. Free hosting can pause when idle and larger conversions can exceed
its memory limits. Test representative documents on the actual host before relying
on it for large jobs.

Set PORT to the assigned listening port and SYGPDF_BIND to 0.0.0.0.
Render supplies RENDER_EXTERNAL_URL automatically. On another host set
SYGPDF_PUBLIC_URL to the complete public HTTPS origin, without a path.
The health endpoint is /healthz. After deployment, open the service URL to use
all 13 tools. The GitHub Pages website continues to serve its browser tools
until the full service URL is confirmed and linked.

For server tools, files leave the browser and are processed on the deployed service.
The hosting provider operates that machine. The app has no document database,
disables access logs, and deletes temporary files after each job. PDF passwords
are sent with the encrypted HTTPS request and aren't stored in a job history.
