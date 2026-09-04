"""Bounded source lookup, not model-generated relevance or curriculum mapping."""
import re

from .document_selection import resolve_chapters
from .schemas import Chapter, SourceSearchHit, SourceSearchResults


STOP_WORDS = frozenset({
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'did', 'do', 'does',
    'explain', 'for', 'from', 'how', 'in', 'is', 'it', 'of', 'on', 'or', 'show',
    'that', 'the', 'this', 'to', 'what', 'when', 'where', 'which', 'who', 'why',
    'with', 'work', 'works',
})


def _context_hit(text: str, chapter: Chapter, first: int, last: int,
                 previous_end: int) -> SourceSearchHit:
    lower = max(chapter.start_character, min(previous_end, first), first - 300)
    newline = text.rfind('\n', lower, first)
    start = newline + 1 if newline >= 0 else lower
    upper = min(chapter.end_character, start + 2000)
    newline = text.find('\n', last, upper)
    end = newline if newline >= 0 else upper
    if last > end:
        # All query terms must remain visible even when a long line forces a
        # bounded window to move forward.
        end = min(chapter.end_character, last + 300)
        start = max(chapter.start_character, end - 2000)
    truncated = ((start > chapter.start_character and text[start - 1] != '\n')
                 or (end < chapter.end_character and text[end] != '\n'))
    return SourceSearchHit(chapter_id=chapter.id, title=chapter.title,
        start_character=start, end_character=end, text=text[start:end],
        match_start=first, match_end=last, context_truncated=truncated)


def _literal_matches(text: str, selected: list[Chapter], query: str, limit: int):
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits = []
    for chapter in selected:
        previous_end = chapter.start_character
        for match in pattern.finditer(text, chapter.start_character, chapter.end_character):
            if match.end() <= previous_end:
                continue
            if len(hits) == limit:
                return hits, True
            hit = _context_hit(text, chapter, match.start(), match.end(), previous_end)
            hits.append(hit)
            previous_end = hit.end_character
    return hits, False


def _topic_terms(query: str) -> list[str]:
    words = re.findall(r"[^\W_]+", query.casefold(), re.UNICODE)
    meaningful = [word for word in words if len(word) >= 2 and word not in STOP_WORDS]
    return list(dict.fromkeys(meaningful))[:8]


def _all_term_matches(text: str, selected: list[Chapter], terms: list[str], limit: int):
    if len(terms) < 2:
        return [], False
    patterns = [re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE) for term in terms]
    hits = []
    for chapter in selected:
        occurrences = [list(pattern.finditer(text, chapter.start_character, chapter.end_character))
                       for pattern in patterns]
        if any(not found for found in occurrences):
            continue
        previous_end = chapter.start_character
        for anchor in occurrences[0]:
            nearest = [min(found, key=lambda match: abs(match.start() - anchor.start()))
                       for found in occurrences[1:]]
            matches = [anchor, *nearest]
            first = min(match.start() for match in matches)
            last = max(match.end() for match in matches)
            if first < previous_end or last - first > 1400:
                continue
            if len(hits) == limit:
                return hits, True
            hit = _context_hit(text, chapter, first, last, previous_end)
            # Moving the bounded window must not exclude any requested term.
            if not all(pattern.search(hit.text) for pattern in patterns):
                continue
            hits.append(hit)
            previous_end = hit.end_character
    return hits, False


def search_source(document_id: str, text: str, chapters: list[Chapter], chapter_ids: list[str],
                  query: str, limit: int = 20) -> SourceSearchResults:
    query = query.strip()
    if not 2 <= len(query) <= 120 or any(ord(character) < 32 for character in query):
        raise ValueError('Enter a topic or phrase of 2 to 120 characters without control characters')
    if not 1 <= limit <= 20:
        raise ValueError('Request between one and twenty search results')
    selected = resolve_chapters(text, chapters, chapter_ids)
    hits, has_more = _literal_matches(text, selected, query, limit)
    mode = 'literal_case_insensitive'
    if not hits:
        hits, has_more = _all_term_matches(text, selected, _topic_terms(query), limit)
        mode = 'all_query_terms_case_insensitive'
    return SourceSearchResults(document_id=document_id, query=query, matches=hits,
                               has_more=has_more, match_mode=mode)
