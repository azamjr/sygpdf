"""Local PDF tools backed by PyMuPDF. Page references in the public API are 1-based."""
from __future__ import annotations

import io
import math
import os
import re
import zipfile
from pathlib import Path
from typing import Iterable

import fitz


MAX_RENDER_PIXELS = 20_000_000


def _doc(item):
    name, data = item
    try:
        d = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open {name or 'PDF'}: {e}") from e
    if d.needs_pass:
        raise ValueError(f"{name or 'PDF'} is password protected; unlock it first")
    return d


def _pdfbytes(doc, **kwargs):
    return doc.tobytes(**kwargs)


def _page_nums(expr, count, *, default_all=False):
    """Parse 1-based comma/semicolon separated pages and inclusive ranges."""
    if expr is None or expr == "":
        return list(range(count)) if default_all else []
    if isinstance(expr, (tuple, list)):
        tokens = []
        for x in expr:
            tokens.extend(str(x).split(','))
    else:
        tokens = re.split(r"[,;\s]+", str(expr).strip())
    out = []
    for token in tokens:
        if not token:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", token)
        if m:
            a, b = map(int, m.groups())
            if a < 1 or b < 1 or a > count or b > count:
                raise ValueError(f"Page range '{token}' is outside 1-{count}")
            out.extend(range(a - 1, b))
        elif token.isdigit():
            p = int(token)
            if not 1 <= p <= count:
                raise ValueError(f"Page {p} is outside 1-{count}")
            out.append(p - 1)
        else:
            raise ValueError(f"Invalid page selection: {token}")
    return out


def _new_from_pages(doc, pages):
    out = fitz.open()
    for p in pages:
        out.insert_pdf(doc, from_page=p, to_page=p)
    return out


def _base(name):
    return Path(name or "document.pdf").stem or "document"


def _zip(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files:
            z.writestr(name, data)
    return b.getvalue()


def _as_rgb(value, default=(0.55, 0.55, 0.55)):
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return tuple(max(0, min(1, float(x))) for x in value)
    return default


def process(tool: str, files: list[tuple[str, bytes]], opts: dict):
    """Run one local PDF operation and return (download_name, bytes).

    tools: merge, split, organize, rotate, compress, protect, unlock,
    watermark, number, pdf2jpg, img2pdf.
    """
    tool = str(tool).lower().replace("-", "").replace("_", "")
    opts = opts or {}
    if not files:
        raise ValueError("Upload at least one file")

    if tool in ("img2pdf", "imagestopdf"):
        from PIL import Image
        out = fitz.open()
        size = str(opts.get("size", "fit")).lower()
        landscape = bool(opts.get("landscape", False))
        if size in ("a4", "letter"):
            page_w, page_h = ((595.28, 841.89) if size == "a4" else (612.0, 792.0))
            if landscape:
                page_w, page_h = page_h, page_w
        else:
            page_w = page_h = None
        for name, raw in files:
            try:
                im = Image.open(io.BytesIO(raw))
                if getattr(im, "n_frames", 1) > 1:
                    im.seek(0)
                im = im.convert("RGB")
                stream = io.BytesIO()
                im.save(stream, format="JPEG", quality=92)
            except Exception as e:
                raise ValueError(f"Could not read image {name}: {e}") from e
            if size == "fit":
                page = out.new_page(width=im.width, height=im.height)
            else:
                page = out.new_page(width=page_w, height=page_h)
            rect = page.rect
            iw, ih = im.size
            scale = min(rect.width / iw, rect.height / ih)
            w, h = iw * scale, ih * scale
            x, y = (rect.width - w) / 2, (rect.height - h) / 2
            page.insert_image(fitz.Rect(x, y, x + w, y + h), stream=stream.getvalue())
        return "images.pdf", _pdfbytes(out, garbage=3, deflate=True)

    # Unlock has to open a protected source without the ordinary unlocked-PDF check.
    if tool == "unlock":
        name, raw = files[0]
        locked = fitz.open(stream=raw, filetype="pdf")
        password = str(opts.get("password", ""))
        if locked.needs_pass and not locked.authenticate(password):
            raise ValueError("Incorrect password")
        return f"{_base(name)}_unlocked.pdf", _pdfbytes(locked, garbage=3, deflate=True)

    docs = [_doc(x) for x in files]
    first_name = files[0][0]
    base = _base(first_name)

    if tool == "merge":
        out = fitz.open()
        for d in docs:
            out.insert_pdf(d)
        return f"{base}_merged.pdf", _pdfbytes(out, garbage=3, deflate=True)

    d = docs[0]
    n = len(d)
    if tool == "split":
        expr = opts.get("pages")
        groups = opts.get("groups")
        if groups:
            groups = list(groups)
        elif expr:
            # Each comma-delimited item is a separate output; range syntax remains available.
            groups = [x.strip() for x in str(expr).split(";") if x.strip()]
            # Commas normally form ranges/selections; explicit semicolons separate groups.
            if len(groups) == 1 and "," in groups[0]:
                groups = [x.strip() for x in groups[0].split(",") if x.strip()]
        else:
            groups = [str(i + 1) for i in range(n)]
        outputs = []
        for i, group in enumerate(groups, 1):
            pages = _page_nums(group, n)
            if not pages:
                continue
            sub = _new_from_pages(d, pages)
            outputs.append((f"{base}_part_{i}.pdf", _pdfbytes(sub, garbage=3, deflate=True)))
        if not outputs:
            raise ValueError("No pages selected")
        if len(outputs) == 1:
            return outputs[0]
        return f"{base}_split.zip", _zip(outputs)

    if tool in ("organize", "reorder", "remove", "extract"):
        pages = _page_nums(opts.get("pages", opts.get("page_order")), n)
        if not pages:
            raise ValueError("Select at least one page")
        out = _new_from_pages(d, pages)
        return f"{base}_organized.pdf", _pdfbytes(out, garbage=3, deflate=True)

    if tool == "rotate":
        angle = int(opts.get("degrees", opts.get("angle", 90)))
        if angle not in (90, 180, 270, -90, -180, -270):
            raise ValueError("Rotation must be 90, 180, or 270 degrees")
        pages = _page_nums(opts.get("pages"), n, default_all=True)
        for p in pages:
            d[p].set_rotation((d[p].rotation + angle) % 360)
        return f"{base}_rotated.pdf", _pdfbytes(d, garbage=3, deflate=True)

    if tool == "compress":
        # Compression is lossless: tiers control duplicate-object cleanup depth.
        quality = str(opts.get("quality", "balanced")).lower()
        garbage = {"high": 2, "balanced": 3, "low": 4}.get(quality, 3)
        if "garbage" in opts:
            garbage = max(0, min(4, int(opts["garbage"])))
        return f"{base}_compressed.pdf", _pdfbytes(d, garbage=garbage, deflate=True, deflate_fonts=True, deflate_images=True)

    if tool == "protect":
        password = str(opts.get("password", ""))
        if not password:
            raise ValueError("Enter a password")
        return f"{base}_protected.pdf", _pdfbytes(d, garbage=3, deflate=True,
            encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password)

    if tool == "watermark":
        text = str(opts.get("text", ""))
        if not text:
            raise ValueError("Enter watermark text")
        opacity = max(0.05, min(1.0, float(opts.get("opacity", 0.28))))
        fontsize = max(8, min(120, float(opts.get("fontsize", 42))))
        color = _as_rgb(opts.get("color"))
        for page in d:
            r = page.rect
            p = fitz.Point(r.width * 0.5, r.height * 0.53)
            width = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
            p = fitz.Point(max(8, (r.width - width) / 2), r.height * 0.53)
            page.insert_text(p, text, fontsize=fontsize, fontname="helv", color=color,
                             overlay=True, fill_opacity=opacity)
        return f"{base}_watermarked.pdf", _pdfbytes(d, garbage=3, deflate=True)

    if tool in ("number", "pagenumbers", "addpagenumbers"):
        start = int(opts.get("start", 1))
        fontsize = max(6, min(48, float(opts.get("fontsize", 11))))
        position = str(opts.get("position", "bottom-center")).lower()
        for i, page in enumerate(d):
            r = page.rect
            label = str(start + i)
            tw = fitz.get_text_length(label, fontname="helv", fontsize=fontsize)
            x = {"bottom-left": 36, "bottom-right": r.width - 36 - tw,
                 "top-center": (r.width - tw) / 2,
                 "bottom-center": (r.width - tw) / 2}.get(position, (r.width - tw) / 2)
            y = 30 if position == "top-center" else r.height - 24
            page.insert_text(fitz.Point(max(6, x), y), label,
                             fontsize=fontsize, fontname="helv", color=(0, 0, 0), overlay=True)
        return f"{base}_numbered.pdf", _pdfbytes(d, garbage=3, deflate=True)

    if tool in ("pdf2jpg", "pdftojpg", "pdf2jpeg"):
        pages = _page_nums(opts.get("pages"), n, default_all=True)
        quality = str(opts.get("quality", "medium")).lower()
        dpi = {"high": 180, "medium": 120, "low": 72}.get(quality, int(opts.get("dpi", 120)))
        dpi = max(36, min(240, int(opts.get("dpi", dpi)))) if "dpi" in opts else dpi
        jpg_quality = {"high": 92, "medium": 82, "low": 68}.get(quality, 85)
        # Bound raster dimensions to avoid pathological uploads exhausting memory.
        outputs = []
        for p in pages:
            page = d[p]
            rect = page.rect
            scale = dpi / 72
            if rect.width * rect.height * scale * scale > MAX_RENDER_PIXELS:
                scale *= math.sqrt(MAX_RENDER_PIXELS / (rect.width * rect.height * scale * scale))
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            outputs.append((f"{base}_page_{p + 1}.jpg", pix.tobytes("jpg", jpg_quality=jpg_quality)))
        if len(outputs) == 1:
            return outputs[0]
        return f"{base}_jpg.zip", _zip(outputs)

    raise ValueError(f"Unsupported tool: {tool}")

