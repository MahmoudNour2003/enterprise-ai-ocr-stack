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

# Initialize PaddleOCR with Arabic & English support and enable_mkldnn=False to fix CPU OneDNN bug
ocr = PaddleOCR(use_angle_cls=True, lang="ar", enable_mkldnn=False)


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
        # If PDF: Render pages to images using PyMuPDF
        if filename.endswith(".pdf") or file.content_type == "application/pdf":
            doc = fitz.open(stream=content, filetype="pdf")
            for page_index in range(len(doc)):
                page = doc[page_index]
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img_np = np.array(img.convert("RGB"))

                result = ocr.ocr(img_np)
                if result and result[0]:
                    lines = [line[1][0] for line in result[0]]
                    text_results.append(
                        f"--- PAGE {page_index + 1} ---\n" + "\n".join(lines)
                    )
        else:
            # If Image (PNG/JPG): Run OCR directly
            img = Image.open(io.BytesIO(content))
            img_np = np.array(img.convert("RGB"))
            result = ocr.ocr(img_np)
            if result and result[0]:
                lines = [line[1][0] for line in result[0]]
                text_results.append("\n".join(lines))

        full_text = "\n\n".join(text_results).strip()
        return {"text": full_text, "output": full_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
