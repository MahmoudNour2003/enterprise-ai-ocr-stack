import io
import logging
import os
import fitz  # PyMuPDF for PDF rendering
from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
import numpy as np
import paddle

# Monkeypatch missing AnalysisConfig.set_optimization_level for PaddleX 3.0 / Python 3.12 compatibility
try:
    if hasattr(paddle, "base") and hasattr(paddle.base, "libpaddle"):
        if not hasattr(
            paddle.base.libpaddle.AnalysisConfig, "set_optimization_level"
        ):
            paddle.base.libpaddle.AnalysisConfig.set_optimization_level = (
                lambda self, level: None
            )
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paddleocr-gpu-service")

# 1. Automatic GPU / CUDA Device Initialization
USE_GPU = paddle.is_compiled_with_cuda()
if USE_GPU:
    try:
        paddle.set_device("gpu")
        logger.info(f"🚀 Lightning AI GPU Enabled: {paddle.get_device()}")
    except Exception as e:
        logger.warning(f"Failed to set GPU device: {e}. Falling back to CPU.")
        paddle.set_device("cpu")
else:
    paddle.set_device("cpu")
    logger.info("ℹ️ Running in CPU mode")

from paddleocr import PaddleOCR

# 2. Clean PaddleOCR Instance Initialization
ocr = PaddleOCR(lang="ar")

app = FastAPI(title="Enterprise PaddleOCR GPU Service")


def prepare_rgb_image(img: Image.Image) -> Image.Image:
    """Safely converts transparent PDF scans (RGBA) onto a solid white background."""
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
    """Sorts text boxes top-to-bottom (Y) and left-to-right (X) to maintain table row structure."""
    if not result:
        return ""

    pages = result if isinstance(result, list) else [result]
    all_lines = []

    for page in pages:
        if not page:
            continue

        # Handle paddleocr output dictionary structure
        if isinstance(page, dict) and "rec_texts" in page:
            texts = page.get("rec_texts", [])
            boxes = page.get("rec_boxes", page.get("dt_polys", []))

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
                        if box.ndim == 2:
                            y_top = float(box[:, 1].min())
                            x_left = float(box[:, 0].min())
                        elif box.ndim == 1 and len(box) >= 4:
                            y_top = float(box[1])
                            x_left = float(box[0])

                    items.append({"y": y_top, "x": x_left, "text": txt_clean})

                items.sort(key=lambda item: (round(item["y"] / 15), item["x"]))
                all_lines.extend([item["text"] for item in items])
            else:
                all_lines.extend([
                    str(t).strip() for t in texts if str(t).strip()
                ])

        # Handle paddleocr output list structure
        elif isinstance(page, list):
            for res in page:
                if isinstance(res, list):
                    for line in res:
                        if isinstance(line, (list, tuple)) and len(line) >= 2:
                            txt = (
                                line[1][0]
                                if isinstance(line[1], (list, tuple))
                                else str(line[1])
                            )
                            if txt.strip():
                                all_lines.append(txt.strip())

    return "\n".join(all_lines).strip()


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "PaddleOCR GPU Service",
        "gpu_enabled": USE_GPU,
        "device": paddle.get_device(),
    }


@app.post("/ocr")
@app.post("/v1/chat/completions")
async def process_document(file: UploadFile = File(...)):
    filename = file.filename if file.filename else "file.pdf"
    content = await file.read()
    logger.info(f"Processing document: {filename} ({len(content)} bytes)")

    text_results = []

    try:
        is_pdf = (
            filename.lower().endswith(".pdf")
            or (file.content_type and "pdf" in file.content_type.lower())
            or content.startswith(b"%PDF")
        )

        if is_pdf:
            doc = fitz.open(stream=content, filetype="pdf")
            logger.info(f"PDF Page count: {len(doc)}")

            for page_index in range(len(doc)):
                page = doc[page_index]
                pix = page.get_pixmap(dpi=200)
                raw_img = Image.open(io.BytesIO(pix.tobytes("png")))
                rgb_img = prepare_rgb_image(raw_img)
                img_np = np.array(rgb_img)

                if hasattr(ocr, "predict"):
                    res = ocr.predict(img_np)
                else:
                    res = ocr.ocr(img_np)

                page_text = parse_paddle_output(res)
                if page_text:
                    text_results.append(
                        f"--- PAGE {page_index + 1} ---\n" + page_text
                    )
        else:
            raw_img = Image.open(io.BytesIO(content))
            rgb_img = prepare_rgb_image(raw_img)
            img_np = np.array(rgb_img)

            if hasattr(ocr, "predict"):
                res = ocr.predict(img_np)
            else:
                res = ocr.ocr(img_np)

            page_text = parse_paddle_output(res)
            if page_text:
                text_results.append(page_text)

        full_extracted_text = "\n\n".join(text_results).strip()
        if not full_extracted_text:
            full_extracted_text = (
                "[NO TEXT DETECTED BY OCR ENGINE ON THIS DOCUMENT]"
            )

        return {"text": full_extracted_text, "output": full_extracted_text}

    except Exception as e:
        logger.error(f"OCR execution error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR error: {str(e)}")
