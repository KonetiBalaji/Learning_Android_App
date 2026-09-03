"""Stable, non-sensitive document recovery codes; never derive codes from input."""
from enum import Enum


class DocumentErrorCode(str, Enum):
    INSUFFICIENT_MATERIAL = 'insufficient_quiz_material'
    EMPTY_PDF_PAGES = 'empty_pdf_pages'
    PDF_COVERAGE_GAP = 'pdf_coverage_gap'
    TOO_MANY_PDF_RANGES = 'too_many_pdf_ranges'


class DocumentValidationError(ValueError):
    def __init__(self, code: DocumentErrorCode, message: str):
        super().__init__(message)
        self.code = code


def document_error_headers(error: Exception) -> dict[str, str] | None:
    if isinstance(error, DocumentValidationError) and isinstance(error.code, DocumentErrorCode):
        return {'X-Learning-Error': error.code.value}
    return None
