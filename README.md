# sygpdf
A single-user PDF toolbox for Ubuntu. Merge, organize and rotate run in the browser. Other tools use the computer serving this application. The interface and assets are bundled. Jobs run one at a time in short-lived processes. PDF jobs pass through memory. Office conversion and OCR also use private temporary directories, removed when the job finishes. The app keeps no job history. Downloads remain wherever you save them. OS swap and browser download history follow your machine's settings.

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
