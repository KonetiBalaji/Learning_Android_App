"""Raster-based OCR; uncertain transcription is never silently approved.

Local recognition does not transmit documents to a provider. OCR models are
downloaded by RapidOCR on first initialization, or warmed before deployment.
"""
import base64
import io
import math
import multiprocessing
import os
from pathlib import Path
import threading
from functools import lru_cache

from .documents import MAX_TEXT, DocumentError, extract, structure

MAX_OCR_PAGES = 50
MAX_PREVIEW_BYTES = 1_500_000
_pdf_slot = threading.BoundedSemaphore(1)


@lru_cache(maxsize=1)
def ocr_engine():
    from rapidocr import RapidOCR
    return RapidOCR(params={"Global.log_level": "error", "Global.model_root_dir": os.getenv("STUDY_MODEL_DIR", str(Path(".study-models").resolve())),
                           "EngineConfig.onnxruntime.intra_op_num_threads": 1, "EngineConfig.onnxruntime.inter_op_num_threads": 1})


def recognize(image, engine=None) -> tuple[str, float]:
    engine = engine or ocr_engine()
    result = engine(image)
    texts = [] if result.txts is None else list(result.txts)
    scores = [] if result.scores is None else list(result.scores)
    if len(texts) != len(scores) or any(not math.isfinite(float(score)) or not 0 <= float(score) <= 1 for score in scores):
        raise DocumentError("OCR returned invalid confidence information. Please retry.")
    return "\n".join(texts), min(map(float, scores), default=0.0)


def analyze(filename: str, content: bytes, *, recognition=None) -> dict:
    pages = extract(filename, content, allow_empty_pdf=True)
    ocr_pages = []
    if filename.lower().endswith(".pdf"):
        missing = [index for index, text in enumerate(pages) if not text.strip()]
        # A scanned body can coexist with a small native header/footer. Do not
        # mistake those few selectable characters for the whole page's content.
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        for index, native in enumerate(pages):
            if index in missing or len(native.strip()) >= 400:
                continue
            resources = reader.pages[index].get("/Resources")
            resources = resources.get_object() if resources is not None else {}
            objects = resources.get("/XObject")
            objects = objects.get_object() if objects is not None else {}
            if any(value.get_object().get("/Subtype") == "/Image" for value in objects.values()):
                missing.append(index)
        missing.sort()
        if len(missing) > MAX_OCR_PAGES:
            raise DocumentError("This PDF needs OCR on more than 50 pages. Split it into smaller PDFs before upload.")
        if missing:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(content)
            try:
                for index in missing:
                    page = pdf[index]
                    try:
                        width, height = page.get_size()
                        if not width > 0 or not height > 0 or not math.isfinite(width + height):
                            raise DocumentError("The scanned PDF has invalid page dimensions.")
                        bitmap = page.render(scale=min(2.5, 1800 / max(width, height)))
                        try:
                            image = bitmap.to_pil().convert("RGB")
                            text, score = (recognition or recognize)(image)
                            if len(text) > 20000:
                                raise DocumentError("OCR text exceeds the 20,000-character per-page limit.")
                            preview = io.BytesIO()
                            image.save(preview, format="JPEG", quality=85)
                            image.close()
                            if preview.tell() > MAX_PREVIEW_BYTES:
                                raise DocumentError("A scanned page exceeds the review image limit.")
                            threshold = float(os.getenv("STUDY_OCR_REVIEW_THRESHOLD", "0.98"))
                            if not 0.5 <= threshold <= 1:
                                raise DocumentError("The server's OCR confidence threshold is invalid.")
                            reviewed = score >= threshold and bool(text.strip())
                            ocr_pages.append({"page": index + 1, "text": text, "confidence": score, "reviewed": reviewed,
                                              "human_reviewed": False, "image_base64": base64.b64encode(preview.getvalue()).decode(),
                                              "image_type": "image/jpeg"})
                            pages[index] = text
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
            finally:
                pdf.close()
    if sum(map(len, pages)) > MAX_TEXT:
        raise DocumentError("Extracted and OCR text exceeds the 2 million character limit.")
    try:
        document = structure(filename, pages)
    except DocumentError:
        if not any(not page["reviewed"] for page in ocr_pages):
            raise
        # An unreadable scan may be manually transcribed against its real image.
        # No passage or question is invented while that review is outstanding.
        document = {"title": Path(filename).stem, "page_count": len(pages), "has_real_pages": True,
                    "structure_confidence": "uncertain", "sections": [], "passages": []}
    document.update(_pages=pages, _ocr_pages=ocr_pages, source_revision=0)
    return update_review_state(document)


def update_review_state(document: dict) -> dict:
    count = sum(not page["reviewed"] for page in document.get("_ocr_pages", []))
    document["ocr_review_count"] = count
    document["ocr_page_count"] = len(document.get("_ocr_pages", []))
    document["processing_state"] = "needs_review" if count else "ready"
    return document


def _worker(pipe, filename, content):
    try:
        from .memory_limits import apply_parser_memory_limit
        apply_parser_memory_limit()
        pipe.send((True, analyze(filename, content)))
    except DocumentError as error:
        pipe.send((False, str(error)))
    except Exception:
        pipe.send((False, "Could not analyze this PDF or its OCR text. Try a clearer or smaller document."))
    finally:
        pipe.close()


def analyze_upload(filename: str, content: bytes) -> dict:
    if not filename.lower().endswith(".pdf"):
        return analyze(filename, content)
    # Native PDF parsing, rasterization, and OCR are all behind the same timeout.
    if not _pdf_slot.acquire(blocking=False):
        raise DocumentError("Another PDF is being analyzed. Please retry shortly.")
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(child, filename, content), daemon=True)
    try:
        process.start()
        child.close()
        timeout = int(os.getenv("STUDY_PDF_TIMEOUT_SECONDS", "180"))
        if not 1 <= timeout <= 180:
            raise DocumentError("The server's PDF processing timeout is invalid.")
        if not parent.poll(timeout):
            raise DocumentError("PDF analysis exceeded its time limit. Split the document and retry.")
        success, result = parent.recv()
        if not success:
            raise DocumentError(result)
        return result
    except (EOFError, OSError) as error:
        raise DocumentError("PDF analysis stopped unexpectedly. Please retry.") from error
    finally:
        parent.close()
        child.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
        _pdf_slot.release()
