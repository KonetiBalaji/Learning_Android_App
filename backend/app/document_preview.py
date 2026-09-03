"""Bounded verbatim previews; page numbers refer to text chunks, not PDF pages."""
from .document_selection import resolve_chapters
from .schemas import Chapter, ChapterPreview

PREVIEW_CHARACTERS = 2000


def preview_chapter(document_id: str, text: str, chapters: list[Chapter], chapter_id: str, page: int) -> ChapterPreview:
    chapter = resolve_chapters(text, chapters, [chapter_id])[0]
    total = (chapter.end_character - chapter.start_character + PREVIEW_CHARACTERS - 1) // PREVIEW_CHARACTERS
    if not 0 <= page < total:
        raise ValueError('Preview page is out of range')
    start = chapter.start_character + page * PREVIEW_CHARACTERS
    end = min(start + PREVIEW_CHARACTERS, chapter.end_character)
    return ChapterPreview(document_id=document_id, chapter_id=chapter_id, title=chapter.title,
                          page=page, total_pages=total, start_character=start, end_character=end, text=text[start:end])
