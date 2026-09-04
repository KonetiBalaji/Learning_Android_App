"""Physical PDF pages mapped back to immutable extracted-source offsets."""
from pathlib import Path
import multiprocessing
import time

import fitz

from .document_selection import resolve_chapters
from .document_errors import DocumentErrorCode, DocumentValidationError
from .schemas import Chapter, PdfPage, PdfPageSelection, SourceRange
from .document_service import apply_parser_memory_limit
from .parser_capacity import parser_slot


def read_pdf_pages(stored: Path, uploads: Path, text: str, max_bytes: int) -> list[PdfPage]:
    if stored.suffix.lower() != '.pdf':
        raise ValueError('Original page selection is available only for PDF documents')
    if stored.is_symlink() or stored.resolve().parent != uploads.resolve():
        raise ValueError('Invalid PDF storage path')
    if len(text) > 2_000_000:
        raise ValueError('PDF text exceeds page-indexing limits')
    with stored.open('rb') as stream:
        content = stream.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError('PDF exceeds page-indexing size limit')
    return _read_pdf_page_content(content, text)


def _read_pdf_page_content(content: bytes, text: str) -> list[PdfPage]:
    pages = []
    extracted = []
    position = 0
    with fitz.open(stream=content, filetype='pdf') as pdf:
        if pdf.needs_pass or not 1 <= len(pdf) <= 1000:
            raise ValueError('PDF is protected or exceeds the page-indexing limit')
        for number, page in enumerate(pdf, start=1):
            page_text = page.get_text('text')
            if len(page_text) > 200_000 or position + len(page_text) > 2_000_000:
                raise ValueError('PDF text exceeds page-indexing limits')
            pages.append(PdfPage(page=number, start_character=position,
                                 end_character=position + len(page_text), has_text=bool(page_text.strip())))
            extracted.append(page_text)
            position += len(page_text) + 1  # Same inter-page newline as upload extraction.
    if '\n'.join(extracted) != text:
        raise ValueError('PDF text no longer matches the stored source; upload it again')
    return pages


def _pdf_pages_worker(pipe, content: bytes, text: str) -> None:
    try:
        apply_parser_memory_limit()
        pages = _read_pdf_page_content(content, text)
        pipe.send(('ok', [page.model_dump() for page in pages]))
    except BaseException:
        pipe.send(('error', None))
    finally:
        pipe.close()


def read_pdf_pages_isolated(stored: Path, uploads: Path, text: str, max_bytes: int,
                            timeout_seconds: int, max_concurrent_parsers: int = 2) -> list[PdfPage]:
    with parser_slot(max_concurrent_parsers):
        return _read_pdf_pages_isolated(stored, uploads, text, max_bytes, timeout_seconds)


def _read_pdf_pages_isolated(stored: Path, uploads: Path, text: str, max_bytes: int,
                             timeout_seconds: int) -> list[PdfPage]:
    if stored.suffix.lower() != '.pdf':
        raise ValueError('Original page selection is available only for PDF documents')
    if stored.is_symlink() or stored.resolve().parent != uploads.resolve():
        raise ValueError('Invalid PDF storage path')
    if len(text) > 2_000_000:
        raise ValueError('PDF text exceeds page-indexing limits')
    with stored.open('rb') as stream:
        content = stream.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError('PDF exceeds page-indexing size limit')
    if not 1 <= timeout_seconds <= 120:
        raise ValueError('Invalid PDF page parsing timeout')
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_pdf_pages_worker, args=(child, content, text), daemon=True)
    process.start()
    child.close()
    deadline = time.monotonic() + timeout_seconds
    try:
        if not parent.poll(max(0.0, deadline - time.monotonic())):
            raise TimeoutError('PDF page parsing exceeded its time limit')
        status, payload = parent.recv()
        if status != 'ok' or not isinstance(payload, list):
            raise ValueError('PDF page parser failed its safety checks')
        return [PdfPage.model_validate(page) for page in payload]
    except TimeoutError:
        raise
    except (EOFError, OSError) as error:
        raise ValueError('PDF page parser stopped unexpectedly') from error
    finally:
        parent.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join(timeout=2)


def select_pdf_pages(document_id: str, text: str, chapters: list[Chapter], pages: list[PdfPage],
                     first: int, last: int) -> PdfPageSelection:
    if not 1 <= first <= last <= len(pages):
        raise ValueError('Choose an ordered range of original PDF pages')
    selected = resolve_chapters(text, chapters, [chapter.id for chapter in chapters])
    start, end = pages[first - 1].start_character, pages[last - 1].end_character
    ranges = []
    position = start
    for chapter in selected:
        left, right = max(start, chapter.start_character), min(end, chapter.end_character)
        if left >= right:
            continue
        if text[position:left].strip():
            raise DocumentValidationError(DocumentErrorCode.PDF_COVERAGE_GAP, 'Selected pages contain omitted source text; repair document structure first')
        if text[left:right].strip():
            ranges.append(SourceRange(chapter_id=chapter.id, start_character=left, end_character=right))
        position = right
    if text[position:end].strip():
        raise DocumentValidationError(DocumentErrorCode.PDF_COVERAGE_GAP, 'Selected pages contain omitted source text; repair document structure first')
    if not ranges:
        raise DocumentValidationError(DocumentErrorCode.EMPTY_PDF_PAGES, 'Selected PDF pages have no extractable text; scanned pages require OCR')
    if len(ranges) > 50:
        raise DocumentValidationError(DocumentErrorCode.TOO_MANY_PDF_RANGES, 'Choose fewer pages, with at most fifty source ranges')
    return PdfPageSelection(document_id=document_id, first_page=first, last_page=last,
        chapter_ids=[part.chapter_id for part in ranges], source_ranges=ranges,
        empty_pages=[page.page for page in pages[first - 1:last] if not page.has_text])
