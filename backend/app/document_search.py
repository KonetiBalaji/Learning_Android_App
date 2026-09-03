"""Literal source lookup, not model-generated topic relevance or curriculum mapping."""
import re

from .document_selection import resolve_chapters
from .schemas import Chapter, SourceSearchHit, SourceSearchResults


def search_source(document_id: str, text: str, chapters: list[Chapter], chapter_ids: list[str],
                  query: str, limit: int = 20) -> SourceSearchResults:
    query = query.strip()
    if not 2 <= len(query) <= 120 or any(ord(character) < 32 for character in query):
        raise ValueError('Enter a literal phrase of 2 to 120 characters without control characters')
    if not 1 <= limit <= 20:
        raise ValueError('Request between one and twenty search results')
    selected = resolve_chapters(text, chapters, chapter_ids)
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits = []
    for chapter in selected:
        previous_end = chapter.start_character
        for match in pattern.finditer(text, chapter.start_character, chapter.end_character):
            if match.end() <= previous_end:
                # One representative match per returned passage, not a count of occurrences.
                continue
            if len(hits) == limit:
                return SourceSearchResults(document_id=document_id, query=query, matches=hits, has_more=True)
            # A match may straddle the prior context limit. Include the complete
            # match even if these two result contexts then overlap slightly.
            lower = max(chapter.start_character, min(previous_end, match.start()), match.start() - 300)
            # Prefer complete source lines/paragraphs while bounding every result.
            newline = text.rfind('\n', lower, match.start())
            start = newline + 1 if newline >= 0 else lower
            upper = min(chapter.end_character, start + 2000)
            newline = text.find('\n', match.end(), upper)
            end = newline if newline >= 0 else upper
            truncated = ((start > chapter.start_character and text[start - 1] != '\n')
                         or (end < chapter.end_character and text[end] != '\n'))
            hits.append(SourceSearchHit(chapter_id=chapter.id, title=chapter.title,
                start_character=start, end_character=end, text=text[start:end],
                match_start=match.start(), match_end=match.end(), context_truncated=truncated))
            previous_end = end
    return SourceSearchResults(document_id=document_id, query=query, matches=hits, has_more=False)
