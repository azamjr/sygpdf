# sygpdf

A web app with 13 PDF tools, including searchable OCR and Office-to-PDF conversion.

**[Open sygpdf](https://sygpdf.onrender.com/)** · [GitHub website](https://azamjr.github.io/sygpdf/) · [Source code](https://github.com/azamjr/sygpdf)

The GitHub website redirects to the full app on Render. All 13 tools are available from the app's sidebar. No app account or local installation is required.

## How to use the app

1. Open [sygpdf](https://sygpdf.onrender.com/). If the free server is waking up, allow extra time for the first load.
2. Select a tool from the sidebar.
3. Click **Choose files**, or drag your files into the upload area.
4. Set the available options. For tools that accept multiple files, use the up/down arrows beside each file to change their order.
5. Click the tool's processing button. Merge, Organize and Rotate use **Process on this device**.
6. Wait for **Your file is ready**. The browser starts the download. You can also click the download link again, or **Preview** for PDF output.
7. Save the result before switching tools or closing the page. The app has no job history or recovery list.

## Available tools

| Tool | How to use it | Result |
| --- | --- | --- |
| Merge PDF | Select multiple PDFs and arrange them with the arrows. | One PDF in the selected order. |
| Split PDF | Select one PDF. Enter page numbers/ranges, or leave the selection empty to split every page. | One PDF or a ZIP containing multiple PDFs. |
| Organize pages | Enter the pages to retain in the order you want, such as `3,1-2`. Omit pages you want removed. | One reordered or shortened PDF. |
| Rotate PDF | Choose 90°, 180° or 270° clockwise. Enter selected pages, or leave blank for all pages. | A rotated PDF. |
| Compress PDF | Select one PDF and a compression setting. | A PDF optimized with lossless cleanup. Savings depend on the input. |
| Protect PDF | Enter a new password for one PDF. | A password-protected PDF using AES-256. |
| Unlock PDF | Enter the current password for one protected PDF. | A PDF with password protection removed. |
| Watermark PDF | Enter short text and choose its opacity. | A PDF with the text stamped across its pages. |
| Page numbers | Choose the position and starting number. | A PDF numbered on every page. |
| PDF to JPG | Choose an image quality setting for one PDF. | One JPG for a single-page document, or a ZIP of page images. |
| Image to PDF | Select JPG, PNG or WebP images, arrange them, and choose Fit image, A4 or Letter. | One PDF containing the images. Landscape applies to fixed page sizes. |
| Office to PDF | Select one Word `.docx`, Excel `.xlsx` or PowerPoint `.pptx` file. | One PDF converted with LibreOffice. |
| Searchable PDF | Select one scanned PDF and choose English, Bahasa Melayu, or both. | A PDF with a searchable/selectable text layer. |

### Page selection examples

Page numbers start at **1**.

- **Organize:** `3,1-2` keeps page 3 first, followed by pages 1 and 2. Pages omitted from the selection are removed.
- **Split:** `1-3,4-6` produces two PDFs, delivered in a ZIP. Leaving the field blank creates a separate PDF for each page.
- **Rotate:** `1,3-5` rotates only those pages. Leaving it blank rotates all pages.

### OCR and conversion notes

Use clear, upright scans and select the correct OCR language. Recognition accuracy depends on the scan and should be checked before relying on extracted text.

OCR renders the original pages as images and adds invisible text. Keep the original PDF if you need its forms, vector artwork, metadata or digital signatures.

Office conversion uses the server's installed fonts and LibreOffice. Review page breaks, spreadsheet print areas, formulas and presentation layouts in the downloaded PDF.

Compression may produce little reduction for an already optimized PDF. Editing a digitally signed PDF can invalidate its signature.

## Limits and troubleshooting

| Situation | What to do |
| --- | --- |
| First load is slow | The free Render service can pause while idle. Wait for it to wake up. |
| Files exceed the limit | The interface allows **32 MiB total per job**, across all selected files. Use smaller files or fewer files. The server also counts form fields toward its upload limit, so stay slightly below 32 MiB. |
| A job is already running | The server handles one conversion job at a time across visitors. Try again after the other job finishes. |
| Processing times out | Server jobs have a **90-second wall-clock limit** and additional CPU/memory limits. Use fewer pages or a smaller file, particularly for OCR. |
| A large conversion fails | The free service has limited resources. Smaller jobs can succeed even when a larger job fails. |
| Incorrect password | Use the current document password. Unlock requires it. Unlock protected files before using the other tools. |
| Invalid page selection | Check that all selected pages exist and use numbers/ranges such as `1,3-5`. |
| Download does not start | Use the result's download link and check the browser's download settings. Multiple results may be packaged as a ZIP. |
| OCR text is inaccurate | Choose the correct language and use a clearer scan. |
| Layout changes after conversion | Check the output against the original, especially fonts, page breaks and spreadsheet print settings. |

Additional server limits include at most **100 input files** and a **128 MiB result**. Office and OCR helpers cap documents at 300 pages, but the time and memory limits can be reached much earlier. Most tools accept one file per job; Merge and Image to PDF accept multiple files.

## File handling and privacy

- **Merge, Organize and Rotate** process documents in your browser. Their files are not sent to the processing API.
- **The other 10 tools** upload files to the sygpdf server over HTTPS. On the online app, this server runs in the owner's Render account.
- PDF jobs pass through memory. Office conversion and OCR also use private temporary directories, cleaned up when the job finishes.
- The app has no document database, saved job history or public file-sharing links. Application HTTP access logging is disabled. Hosting infrastructure may maintain its own operational logs.
- Conversion workers receive a restricted environment without the application's hosting credentials. Office and OCR workers block Internet sockets.
- Passwords are sent with the HTTPS processing request and are not stored in a job history.
- Downloads remain wherever you save them on your device.

Render operates the hosting infrastructure. For documents that must stay entirely on your own machine, run the full app locally using the instructions below.

## Current hosting configuration

| Setting | Current configuration |
| --- | --- |
| Application URL | `https://sygpdf.onrender.com/` |
| GitHub Pages URL | `https://azamjr.github.io/sygpdf/`, redirects to the full app |
| Source branch | `main` in `azamjr/sygpdf` |
| Render service | `sygpdf` |
| Runtime | Docker, Python 3.13 base image |
| Compute plan | Free |
| Region | Singapore |
| Bind address | `0.0.0.0` |
| Port | `10000` on Render; `8765` by default locally |
| Persistent disk/database | None |
| App health endpoint | `GET /healthz` |
| Render health probe | Default TCP probe on the current service. The Blueprint specifies `/healthz` for a future Blueprint deployment. |

The existing Render service was created directly. `render.yaml` provides a reproducible starting configuration for a new Blueprint deployment; changing that file alone does not reconfigure the current service.

### Environment variables

| Variable | Purpose |
| --- | --- |
| `SYGPDF_BIND` | Listening address. Use `0.0.0.0` in a hosted container. Defaults to `127.0.0.1`. |
| `PORT` | Listening port. Set to `10000` on Render. Defaults to `8765`. |
| `RENDER_EXTERNAL_URL` | Render supplies the public HTTPS origin automatically. |
| `SYGPDF_PUBLIC_URL` | Optional public HTTPS origin for another host or a custom domain, without a path. Takes precedence over `RENDER_EXTERNAL_URL`. |

### Publishing changes

1. Commit and push changes to `main`.
2. Check the PDF test and Pages workflow results under [GitHub Actions](https://github.com/azamjr/sygpdf/actions).
3. For backend or interface changes, check the [Render service](https://dashboard.render.com/web/srv-dbq880m7bikc73d8q3tg) and its deployed commit. Auto-deploy is configured, but public-repository connections may need **Manual Deploy → Deploy latest commit**.
4. Wait for the deployment to become live, then check `/healthz` and the affected tool.
5. The Pages workflow publishes `docs/`; its landing page redirects visitors to Render.

For documentation-only commits, `[skip render]` in the commit message avoids an unnecessary Render auto-deploy.

## Run locally with Docker on Windows, macOS or Linux

Local Docker runs all 13 tools on your computer, including Office conversion and English/Malay OCR. Docker supplies the Linux environment required by the conversion worker. You do not need to install Python, LibreOffice or Tesseract on the host.

The initial installation/build and later updates need Internet access. After the image is built, the app can process documents offline. Keep Docker running and open **http://127.0.0.1:8765** for local processing. The Render URL always uses the online service.

### 1. Install Docker for your operating system

| Operating system | Setup |
| --- | --- |
| Windows | Install Docker Desktop using its WSL 2 backend. Use Linux containers. |
| macOS | Install Docker Desktop matching your Mac's Apple silicon or Intel processor. |
| Ubuntu and other Linux distributions | Install Docker Engine with the Docker Compose plugin using the instructions for your distribution. Docker Desktop for Linux is also an option. |

Check Docker's current operating system and hardware requirements before installing.

- [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
- [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
- [Docker Engine for Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Engine for other Linux distributions](https://docs.docker.com/engine/install/)

**Windows**

1. If WSL is not installed, open PowerShell as Administrator and run:

   ```powershell
   wsl --install
   ```

2. Restart Windows if requested. Update WSL:

   ```powershell
   wsl --update
   ```

3. Install and launch Docker Desktop. Enable **Use the WSL 2 based engine** in its settings where available. Ensure it is using Linux containers.
4. Install [Git for Windows](https://git-scm.com/downloads/win) if you want to use the Git download method below. Open a new PowerShell window after installation.

**macOS**

1. Choose **Apple menu → About This Mac** to identify Apple silicon or Intel.
2. Install the matching Docker Desktop download and open Docker from Applications. Complete its first-start setup.
3. Open Terminal. Run `git --version`. If macOS offers to install command line developer tools, complete that installation before cloning, or use the ZIP download method below.

**Linux**

1. Follow the official installation guide for your distribution, including the Compose plugin.
2. Start the Docker service as described in that guide and install Git using your distribution's package manager.
3. If Docker commands require administrator access, prefix each `docker` command below with `sudo`, including verification, startup, logs and shutdown.

### 2. Verify Docker is ready

Launch Docker Desktop on Windows/macOS and wait for the engine to start. In PowerShell or Terminal, run:

```sh
docker version
docker compose version
```

The first command should show both client and server information. The second should report a Compose version.

### 3. Download and start sygpdf

Run these commands in PowerShell on Windows, or Terminal on macOS/Linux:

```sh
git clone https://github.com/azamjr/sygpdf.git
cd sygpdf
docker compose up --build -d
```

Alternatively, choose **Code → Download ZIP** on the [repository](https://github.com/azamjr/sygpdf), extract it, then open a terminal in the extracted folder containing `compose.yaml`. Run `docker compose up --build -d` there.

The first build downloads the image and dependencies and can take several minutes. Docker includes LibreOffice, Tesseract, English/Malay OCR data and the Python packages.

Check that the service is running:

```sh
docker compose ps
```

Open **http://127.0.0.1:8765**. Select a tool, choose files, adjust its options, process and save the result. All 13 tools are available locally. The regular file-size and processing-time limits still apply.

To check the web service, open **http://127.0.0.1:8765/healthz** in your browser. It should return `"status": "ok"`. Verify conversion with a small sample document as well.

### Start, stop and update

Run these commands from the folder containing `compose.yaml`.

| Action | Command |
| --- | --- |
| Start an already built app | `docker compose up -d` |
| View logs | `docker compose logs --tail=100 sygpdf` |
| Stop the app | `docker compose stop` |
| Remove the stopped/running app container | `docker compose down` |

To update a Git checkout:

```sh
git pull --ff-only
docker compose up --build -d
```

Save any local edits before updating. If you downloaded a ZIP, download the latest ZIP into a separate folder. Run `docker compose down` in the old folder, then build/start from the new folder.

Keep Docker running while using the app. After restarting your computer, start Docker and run `docker compose up -d` again.

### Local privacy and troubleshooting

The Compose configuration publishes the app only on `127.0.0.1` and mounts no host document folders. Files selected in the local interface are processed in the browser or the local container. Job temporary files are cleaned up after processing. Downloads remain in the location selected in your browser.

Local processing reduces exposure to hosting providers. Your computer, browser extensions, backup tools and any cloud-synced download folders still affect document privacy. Use a local folder outside cloud sync when documents must stay on the device.

| Problem | Resolution |
| --- | --- |
| Cannot connect to Docker daemon | Start Docker Desktop or the Linux Docker service, wait for it to be ready, then retry. |
| Windows WSL/virtualization error | Check Docker's Windows requirements, enable hardware virtualization if needed, update WSL and restart. |
| Docker reports a Windows container/image mismatch | Switch Docker Desktop to Linux containers. |
| `docker compose` is unavailable | Install/update Docker Desktop or the Linux Compose plugin. |
| Linux permission denied connecting to Docker | Run the Docker commands with `sudo`, or follow Docker's documented user-access setup. |
| No configuration file found | Change directory to the extracted/cloned folder containing `compose.yaml`. |
| Port 8765 already allocated | Stop the other application/container using that port, then retry. |
| Build download fails | Check Internet access and retry `docker compose up --build -d`. |
| App fails after startup | Check `docker compose ps` and `docker compose logs --tail=100 sygpdf`. |
| Large OCR/Office conversion fails | Try fewer pages. The app has worker limits, a 64 MiB temporary filesystem and a 1536 MiB container memory limit. |

Windows and macOS instructions use the repository's Linux Docker image. Native Python execution on those operating systems is not supported by the current Linux-specific worker.

## Run directly on Ubuntu

Use Python 3.12 or later. Install the native conversion tools and OCR data:

```sh
sudo apt update
sudo apt install python3-venv libreoffice-writer libreoffice-calc libreoffice-impress tesseract-ocr tesseract-ocr-eng tesseract-ocr-msa libseccomp2 fonts-dejavu-core
git clone https://github.com/azamjr/sygpdf.git
cd sygpdf
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open **http://127.0.0.1:8765** and keep the terminal running while using the app.

## Developer reference

- `app.py` serves the interface, health endpoint and processing API.
- `static/index.html` contains the full 13-tool interface.
- `static/assets/local.js` runs the three browser tools.
- `engine.py` handles the core server PDF operations.
- `advanced.py` handles LibreOffice conversion and OCR.
- `worker.py` runs each server job in a separate, bounded process.
- `Dockerfile` installs native and Python dependencies.
- `compose.yaml` configures local Docker usage.
- `render.yaml` describes a starting Render Blueprint.
- `docs/index.html` redirects GitHub Pages to the full online app.

### Health and API

```sh
curl https://sygpdf.onrender.com/healthz
```

The health endpoint returns `status: ok` and the available server tool IDs. It confirms that the web app responds; use an actual conversion to verify a processing engine.

`POST /api/process` accepts multipart form fields `tool`, repeated `files`, and optional `opts` containing a JSON object. Successful requests return a downloadable file. Browser requests must come from the configured origin.

### Verification

With the dependencies installed, run:

```sh
python tests/check.py
python tests/hosting.py
```

The functional checks use synthetic documents to verify the 13 processing operations. Hosting checks cover the interface, assets, health endpoint and origin restrictions.

Initial live verification covered all 13 processing operations, Word/Excel/PowerPoint files, and English/Malay OCR. Individual document complexity can still affect conversion accuracy, runtime and memory use.

## Scope and dependencies

Current features are the 13 tools listed above. Permanent redaction, PDF/A conversion, editable PDF-to-Office conversion, HTML-to-PDF conversion, repair and signature workflows are not implemented.

The app uses aiohttp, PyMuPDF, Pillow, pdf-lib, LibreOffice and Tesseract. Dependency versions are recorded in `requirements.txt` and the Dockerfile. Review each dependency's license before redistribution or commercial hosting. PyMuPDF offers AGPL and commercial licensing; its license does not by itself establish a license for this repository's original code.
