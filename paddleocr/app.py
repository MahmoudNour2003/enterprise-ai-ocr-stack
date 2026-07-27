import io
import logging
import os
import fitz  # PyMuPDF for PDF page rendering
from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paddleocr-service")

# Disable buggy OneDNN / PIR executor conversion on CPU
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_onednn"] = "0"

from paddleocr import PaddleOCR

app = FastAPI(title="PaddleOCR Service")

# Standard official PaddleOCR initialization (Arabic + English + Numbers)
ocr = PaddleOCR(lang="ar", enable_mkldnn=False)


def parse_paddle_output(result) -> str:
    """Parses all text lines from PaddleOCR output reliably."""
    if not result:
        return ""

    lines = []
    # If list of pages or single page
    pages = result if isinstance(result, list) else [result]

    for page in pages:
        if not page:
            continue
        for line in page:
            if not line:
                continue
            try:
                # Format: [ [box_coords], (text, confidence) ]
                if isinstance(line, (list, tuple)) and len(line) >= 2:
                    text_info = line[1]
                    if (
                        isinstance(text_info, (list, tuple))
                        and len(text_info) >= 1
                    ):
                        txt = str(text_info[0]).strip()
                    else:
                        txt = str(text_info).strip()

                    if txt:
                        lines.append(txt)
            except Exception as e:
                logger.error(f"Error parsing line: {e}")
                continue

    return "\n".join(lines).strip()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "PaddleOCR ready"}


@app.post("/ocr")
@app.post("/v1/chat/completions")
async def process_document(file: UploadFile = File(...)):
    filename = file.filename if file.filename else "file.pdf"
    content = await file.read()
    logger.info(f"Received file: {filename}, size: {len(content)} bytes")

    text_results = []

    try:
        # Check if file is PDF (by extension or binary header %PDF)
        is_pdf = (
            filename.lower().endswith(".pdf")
            or (file.content_type and "pdf" in file.content_type.lower())
            or content.startswith(b"%PDF")
        )

        if is_pdf:
            logger.info("Processing document as PDF...")
            doc = fitz.open(stream=content, filetype="pdf")
            logger.info(f"PDF page count: {len(doc)}")

            for page_index in range(len(doc)):
                page = doc[page_index]

                # Render page at 200 DPI
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img_np = np.array(img.convert("RGB"))

                # Run PaddleOCR
                res = ocr.ocr(img_np)
                txt = parse_paddle_output(res)
                logger.info(
                    f"Page {page_index + 1} extracted {len(txt)} chars"
                )

                if txt:
                    text_results.append(
                        f"--- PAGE {page_index + 1} ---\n" + txt
                    )
        else:
            logger.info("Processing document as Image...")
            img = Image.open(io.BytesIO(content))
            img_np = np.array(img.convert("RGB"))

            res = ocr.ocr(img_np)
            txt = parse_paddle_output(res)
            logger.info(f"Image extracted {len(txt)} chars")

            if txt:
                text_results.append(txt)

        full_extracted_text = "\n\n".join(text_results).strip()
        logger.info(f"Total extracted text length: {len(full_extracted_text)}")

        if not full_extracted_text:
            logger.warning("OCR detected 0 characters!")
            full_extracted_text = (
                "[NO TEXT DETECTED BY OCR ENGINE ON THIS DOCUMENT]"
            )

        return {"text": full_extracted_text, "output": full_extracted_text}

    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"OCR error: {str(e)}"
        )
