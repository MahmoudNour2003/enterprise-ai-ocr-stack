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

app = FastAPI(title="PaddleOCR Maximum Coverage CPU Service")

# Initialize PaddleOCR with high-sensitivity detection thresholds to capture ALL faint/small text
ocr = PaddleOCR(
    use_angle_cls=False,
    lang="ar",
    enable_mkldnn=False,
    det_db_thresh=0.2,
    det_db_box_thresh=0.5,
    unclip_ratio=2.0,
    det_limit_side_len=1280,
)


def extract_all_ocr_text(ocr_result) -> str:
    """Extracts all text lines from PaddleOCR result without missing any text."""
    if not ocr_result:
        return ""

    extracted_lines = []

    # Handle multi-page or single-page list structure
    pages = ocr_result if isinstance(ocr_result, list) else [ocr_result]

    for page in pages:
        if not page:
            continue
        for line in page:
            if not line:
                continue
            try:
                # Format: [ [box_coords], (text, confidence) ]
                if isinstance(line, (list, tuple)) and len(line) >= 2:
                    text_part = line[1]
                    if (
                        isinstance(text_part, (list, tuple))
                        and len(text_part) >= 1
                    ):
                        txt = str(text_part[0]).strip()
                    else:
                        txt = str(text_part).strip()

                    if txt:
                        extracted_lines.append(txt)
            except Exception:
                continue

    return "\n".join(extracted_lines).strip()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "PaddleOCR Maximum Coverage Ready"}


@app.post("/ocr")
@app.post("/v1/chat/completions")
async def process_document(file: UploadFile = File(...)):
    filename = file.filename.lower() if file.filename else "doc.pdf"
    content = await file.read()
    text_results = []

    try:
        # If PDF: Render pages to images using PyMuPDF at crisp 200 DPI
        if filename.endswith(".pdf") or file.content_type == "application/pdf":
            doc = fitz.open(stream=content, filetype="pdf")
            for page_index in range(len(doc)):
                page = doc[page_index]
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img_np = np.array(img.convert("RGB"))

                result = ocr.ocr(img_np)
                page_text = extract_all_ocr_text(result)
                if page_text:
                    text_results.append(
                        f"--- PAGE {page_index + 1} ---\n" + page_text
                    )
        else:
            # If Image (PNG/JPG): Run OCR directly
            img = Image.open(io.BytesIO(content))
            img_np = np.array(img.convert("RGB"))
            result = ocr.ocr(img_np)
            page_text = extract_all_ocr_text(result)
            if page_text:
                text_results.append(page_text)

        full_text = "\n\n".join(text_results).strip()
        return {"text": full_text, "output": full_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
