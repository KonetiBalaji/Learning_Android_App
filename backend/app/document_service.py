from __future__ import annotations

import asyncio
import multiprocessing
import re
import time
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import fitz
from docx import Document
from fastapi import HTTPException, UploadFile, status

from .config import Settings
from .schemas import Chapter
from .document_limits import validate_docx_archive
from .docx_text import extract_docx_body
from .document_errors import DocumentErrorCode, DocumentValidationError, document_error_headers
from .file_cleanup import discard_uncommitted_upload

ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt"}
HEADING_PATTERN = re.compile(r"(?m)^(?:chapter|unit|section)\s+(?:\d+|[ivxlcdm]+)\b[^\n]*|^\d+(?:\.\d+)*\s+[^\n]{3,}$", re.IGNORECASE)
MAX_EXTRACTED_CHARACTERS = 2_000_000
PARSER_MEMORY_BYTES = 1024 * 1024 * 1024


class DocumentProcessingLimit(ValueError):
    pass


async def validate_and_store(upload: UploadFile, settings: Settings) -> tuple[Path, str, str]:
    filename = Path(upload.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF, DOCX, and TXT files are supported")
    content = await upload.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Documents must not exceed 50 MB")
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The uploaded file is empty")
    stored = settings.uploads_dir / f"{uuid.uuid4()}-{os_safe_stem(filename)}{suffix}"
    try:
        if suffix == '.docx':
            # Keep cheap archive admission in the request worker so oversized input
            # is rejected before paying process startup cost. The child repeats it.
            validate_docx_archive(content)
        text = await asyncio.to_thread(
            extract_text_isolated, content, suffix, settings.document_parse_timeout_seconds)
    except (TimeoutError, DocumentProcessingLimit) as error:
        validation = DocumentValidationError(
            DocumentErrorCode.DOCUMENT_PROCESSING_LIMIT,
            'The document exceeded safe processing limits.',
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=str(validation), headers=document_error_headers(validation)) from error
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="The document could not be processed. It may be corrupt, protected, or exceed processing limits.") from error
    if len(text.strip()) < 80:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The document has too little extractable text; scanned or protected files are not supported in this MVP")
    try:
        stored.write_bytes(content)
    except OSError as error:
        discard_uncommitted_upload(settings, stored)
        raise HTTPException(status_code=503, detail="Document storage is temporarily unavailable. Please retry.") from error
    return stored, filename, text


def os_safe_stem(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", Path(filename).stem).strip("-")[:80] or "document"


def extract_text(content: bytes, suffix: str) -> str:
    if suffix == ".txt":
        return content.decode("utf-8", errors="replace")
    if suffix == ".docx":
        if not zipfile.is_zipfile(BytesIO(content)):
            raise ValueError("The DOCX archive is invalid")
        validate_docx_archive(content)
        document = Document(BytesIO(content))
        return extract_docx_body(document)
    pdf = fitz.open(stream=content, filetype="pdf")
    try:
        if pdf.needs_pass:
            raise ValueError("Password-protected PDFs are not supported")
        return "\n".join(page.get_text("text") for page in pdf)
    finally:
        pdf.close()


def _bounded_extract_worker(pipe, content: bytes, suffix: str) -> None:
    try:
        apply_parser_memory_limit()
        text = extract_text(content, suffix)
        if len(text) > MAX_EXTRACTED_CHARACTERS:
            pipe.send(('limit', None))
        else:
            pipe.send(('ok', text))
    except BaseException:
        pipe.send(('error', None))
    finally:
        pipe.close()


def apply_parser_memory_limit() -> None:
    try:
        import resource
        _, current_hard = resource.getrlimit(resource.RLIMIT_AS)
        ceiling = min(PARSER_MEMORY_BYTES, current_hard) if current_hard > 0 else PARSER_MEMORY_BYTES
        resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
    except (ImportError, OSError, ValueError):
        # Windows has no resource module; the parent still enforces wall time
        # and terminates this isolated process on timeout.
        pass


def extract_text_isolated(content: bytes, suffix: str, timeout_seconds: int) -> str:
    """Parse untrusted content out of process and return only bounded text."""
    if suffix not in ALLOWED_SUFFIXES or not 1 <= timeout_seconds <= 120:
        raise ValueError('Invalid isolated document parsing request')
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_bounded_extract_worker, args=(child, content, suffix), daemon=True)
    process.start()
    child.close()
    deadline = time.monotonic() + timeout_seconds
    try:
        remaining = max(0.0, deadline - time.monotonic())
        if not parent.poll(remaining):
            raise TimeoutError('Document parsing exceeded its time limit')
        status, text = parent.recv()
        if status == 'limit':
            raise DocumentProcessingLimit('Extracted text exceeds its safe limit')
        if status != 'ok' or not isinstance(text, str):
            raise ValueError('Document parsing failed its safety checks')
        return text
    except TimeoutError:
        raise
    except (EOFError, OSError) as error:
        raise ValueError('Document parser stopped unexpectedly') from error
    finally:
        parent.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join(timeout=2)


def detect_chapters(text: str) -> list[Chapter]:
    matches = list(HEADING_PATTERN.finditer(text))
    if not matches:
        return [Chapter(id="whole-document", title="Whole document", start_character=0, end_character=len(text), confidence=0.35)]
    chapters: list[Chapter] = []
    if text[:matches[0].start()].strip():
        chapters.append(Chapter(id="document-introduction", title="Introduction / before first heading",
                                start_character=0, end_character=matches[0].start(), confidence=0.55))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(0).strip()[:160]
        # Small sections can contain important definitions. Keep their source
        # range and report lower confidence instead of silently discarding it.
        chapters.append(Chapter(id=f"chapter-{index + 1}", title=title, start_character=match.start(),
                                end_character=end, confidence=0.85 if end - match.start() >= 80 else 0.55))
    return chapters or [Chapter(id="whole-document", title="Whole document", start_character=0, end_character=len(text), confidence=0.35)]
