FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer libreoffice-calc libreoffice-impress tesseract-ocr-eng tesseract-ocr-msa libseccomp2 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py worker.py advanced.py engine.py ./
COPY static ./static
ENV SYGPDF_BIND=0.0.0.0 PYTHONDONTWRITEBYTECODE=1
USER 65534:65534
CMD ["python","app.py"]
