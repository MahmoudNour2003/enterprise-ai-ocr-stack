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

# Initialize PaddleOCR 2.7+
ocr = PaddleOCR(lang="ar", enable_mkldnn=False)


def prepare_rgb_image(img: Image.Image) -> Image.Image:
    """Safely converts RGBA/transparent images to RGB with a solid white background.

    Prevents transparent PDF page scans from turning into solid black images.
    """
    if img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    ):
        try:
            alpha = img.convert("RGBA").split()[-1]
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=alpha)
            return bg
        except Exception:
            return img.convert("RGB")
    return img.convert("RGB")


def parse_paddle_output(result) -> str:
    """Spatially sorts text boxes by Y-coordinate (top-to-bottom) and X-coordinate (left-to-right) to preserve table row order."""
    if not result:
        return ""

    pages = result if isinstance(result, list) else [result]
    all_lines = []

    for page in pages:
        if not page:
            continue

        # PaddleOCR 2.7+ / PaddleX dict format: page['rec_texts'] and page['rec_boxes'] / page['dt_polys']
        if isinstance(page, dict) and "rec_texts" in page:
            texts = page.get("rec_texts", [])
            boxes = page.get("rec_boxes", page.get("dt_polys", []))

            # Pair text with spatial coordinates
            items = []
            if (
                isinstance(boxes, (list, np.ndarray))
                and len(boxes) == len(texts)
            ):
                for box, txt in zip(boxes, texts):
                    txt_clean = str(txt).strip()
                    if not txt_clean:
                        continue
                    y_top, x_left = 0, 0
                    if isinstance(box, np.ndarray):
                        if box.ndim == 2:  # Bounding polygon [[x1,y1], [x2,y2], ...]
                            y_top = float(box[:, 1].min())
                            x_left = float(box[:, 0].min())
                        elif box.ndim == 1 and len(box) >= 4:  # [x1, y1, x2, y2]
                            y_top = float(box[1])
                            x_left = float(box[0])

                    items.append({"y": y_top, "x": x_left, "text": txt_clean})

                # Sort spatially: Top-to-Bottom by Y (thresholding lines by ~15px), then Left-to-Right by X
                items.sort(key=lambda item: (round(item["y"] / 15), item["x"]))
                all_lines.extend([item["text"] for item in items])
            else:
                all_lines.extend([
                    str(t).strip() for t in texts if str(t).strip()
                ])

    return "\n".join(all_lines).strip()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "PaddleOCR 2.7+ ready"}


@app.post("/ocr")
@app.post("/v1/chat/completions")
async def process_document(file: UploadFile = File(...)):
    filename = file.filename if file.filename else "file.pdf"
    content = await file.read()
    logger.info(f"Received file: {filename}, size: {len(content)} bytes")

    text_results = []

    try:
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
                raw_img = Image.open(io.BytesIO(pix.tobytes("png")))
                rgb_img = prepare_rgb_image(raw_img)
                img_np = np.array(rgb_img)

                # Run PaddleOCR predict
                res = ocr.predict(img_np)
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
            raw_img = Image.open(io.BytesIO(content))
            rgb_img = prepare_rgb_image(raw_img)
            img_np = np.array(img.convert("RGB"))

            res = ocr.predict(img_np)
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
