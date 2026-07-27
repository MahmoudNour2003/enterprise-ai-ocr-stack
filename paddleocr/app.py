import io
import os
import fitz  # PyMuPDF for PDF page rendering
from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
import numpy as np

# Disable buggy OneDNN / PIR executor conversion on CPU
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_onednn"] = "0"

from paddleocr import PaddleOCR

app = FastAPI(title="PaddleOCR CPU Service")

# Initialize PaddleOCR with lang="ar" and det_limit_side_len=960
ocr = PaddleOCR(
    use_angle_cls=False,
    lang="ar",
    enable_mkldnn=False,
    det_limit_side_len=960,
)


def resize_image_if_large(img: Image.Image, max_dim: int = 1920) -> Image.Image:
    """Proportionally resizes large images to prevent excessive memory allocation."""
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        new_w = int(w * scale)
        new_h = int(h * scale)
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    return img


def group_ocr_lines_horizontally(ocr_result, y_threshold: int = 15) -> str:
    """Defensively sorts and groups OCR bounding boxes into horizontal lines.

    Stitches individual characters/words on the same Y-level into complete
    sentences.
    """
    if not ocr_result or not ocr_result[0]:
        return ""

    boxes_text = []
    for item in ocr_result[0]:
        if not item:
            continue
        try:
            if len(item) >= 2 and isinstance(item[0], list):
                box = item[0]
                text_info = item[1]
                text_str = (
                    text_info[0]
                    if isinstance(text_info, (list, tuple))
                    else str(text_info)
                )
                y_top = box[0][1] if len(box) > 0 and len(box[0]) > 1 else 0
                x_left = box[0][0] if len(box) > 0 and len(box[0]) > 0 else 0
            elif (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and isinstance(item[0], str)
            ):
                text_str = item[0]
                y_top, x_left = 0, 0
            else:
                continue

            text_clean = str(text_str).strip()
            if text_clean:
                boxes_text.append({"x": x_left, "y": y_top, "text": text_clean})
        except Exception:
            continue

    if not boxes_text:
        return ""

    # Sort boxes by Y coordinate first
    boxes_text.sort(key=lambda b: b["y"])

    # Group boxes into lines based on Y coordinate threshold
    lines = []
    current_line = [boxes_text[0]]

    for box in boxes_text[1:]:
        if abs(box["y"] - current_line[0]["y"]) < y_threshold:
            current_line.append(box)
        else:
            # Sort current line boxes by X coordinate (left to right)
            current_line.sort(key=lambda b: b["x"])
            line_str = " ".join([b["text"] for b in current_line])
            lines.append(line_str)
            current_line = [box]

    if current_line:
        current_line.sort(key=lambda b: b["x"])
        line_str = " ".join([b["text"] for b in current_line])
        lines.append(line_str)

    return "\n".join(lines)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "PaddleOCR CPU ready"}


@app.post("/ocr")
@app.post("/v1/chat/completions")
async def process_document(file: UploadFile = File(...)):
    filename = file.filename.lower() if file.filename else "doc.pdf"
    content = await file.read()
    text_results = []

    try:
        # If PDF: Render pages to images using PyMuPDF at 200 DPI
        if filename.endswith(".pdf") or file.content_type == "application/pdf":
            doc = fitz.open(stream=content, filetype="pdf")
            for page_index in range(len(doc)):
                page = doc[page_index]
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img = resize_image_if_large(img)
                img_np = np.array(img.convert("RGB"))

                result = ocr.ocr(img_np)
                page_text = group_ocr_lines_horizontally(result)
                if page_text:
                    text_results.append(
                        f"--- PAGE {page_index + 1} ---\n" + page_text
                    )
        else:
            # If Image (PNG/JPG): Run OCR directly
            img = Image.open(io.BytesIO(content))
            img = resize_image_if_large(img)
            img_np = np.array(img.convert("RGB"))
            result = ocr.ocr(img_np)
            page_text = group_ocr_lines_horizontally(result)
            if page_text:
                text_results.append(page_text)

        full_text = "\n\n".join(text_results).strip()
        return {"text": full_text, "output": full_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
