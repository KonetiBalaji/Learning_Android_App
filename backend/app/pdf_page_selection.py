"""Physical PDF pages mapped back to immutable extracted-source offsets."""
from pathlib import Path

import fitz

from .document_selection import resolve_chapters
from .document_errors import DocumentErrorCode, DocumentValidationError
from .schemas import Chapter, PdfPage, PdfPageSelection, SourceRange


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
