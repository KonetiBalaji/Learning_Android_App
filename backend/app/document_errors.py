"""Stable, non-sensitive document recovery codes; never derive codes from input."""
from enum import Enum


class DocumentErrorCode(str, Enum):
    INSUFFICIENT_MATERIAL = 'insufficient_quiz_material'
    EMPTY_PDF_PAGES = 'empty_pdf_pages'
    PDF_COVERAGE_GAP = 'pdf_coverage_gap'
    TOO_MANY_PDF_RANGES = 'too_many_pdf_ranges'
    DOCUMENT_COUNT_LIMIT = 'document_count_limit'
    DOCUMENT_BYTES_LIMIT = 'document_bytes_limit'
    DOCUMENT_PROCESSING_LIMIT = 'document_processing_limit'
    DOCUMENT_PROCESSING_BUSY = 'document_processing_busy'


class DocumentValidationError(ValueError):
    def __init__(self, code: DocumentErrorCode, message: str):
        super().__init__(message)
        self.code = code


def document_error_headers(error: Exception) -> dict[str, str] | None:
    if isinstance(error, DocumentValidationError) and isinstance(error.code, DocumentErrorCode):
        return {'X-Learning-Error': error.code.value}
    return None
