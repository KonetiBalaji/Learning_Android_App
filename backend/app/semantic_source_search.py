"""Bounded semantic retrieval that returns only verbatim selected source ranges."""
from __future__ import annotations

from dataclasses import dataclass
import math

from openai import OpenAI

from .document_selection import resolve_chapters
from .schemas import Chapter, SourceSearchHit, SourceSearchResults


MAX_SOURCE_CHARACTERS = 80_000
MAX_PASSAGE_CHARACTERS = 1_600
MIN_SIMILARITY = 0.35


class SemanticSearchUnavailable(RuntimeError):
    pass


class SemanticSearchScopeTooLarge(ValueError):
    pass


@dataclass(frozen=True)
class Candidate:
    chapter: Chapter
    start: int
    end: int
    truncated: bool


def _candidates(text: str, selected: list[Chapter]) -> list[Candidate]:
    if sum(chapter.end_character - chapter.start_character for chapter in selected) > MAX_SOURCE_CHARACTERS:
        raise SemanticSearchScopeTooLarge(
            'Semantic search source is too large; select fewer or smaller chapters')
    result: list[Candidate] = []
    for chapter in selected:
        start = chapter.start_character
        while start < chapter.end_character:
            ceiling = min(start + MAX_PASSAGE_CHARACTERS, chapter.end_character)
            if ceiling < chapter.end_character:
                boundary = text.rfind('\n', start + 1, ceiling + 1)
                end = boundary if boundary > start else ceiling
            else:
                end = ceiling
            if text[start:end].strip():
                result.append(Candidate(chapter, start, end,
                    (start > chapter.start_character and text[start - 1] != '\n')
                    or (end < chapter.end_character and text[end] != '\n')))
            start = end + int(end < chapter.end_character and text[end] == '\n')
    return result


def _similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise SemanticSearchUnavailable('Embedding dimensions did not match')
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool)
               for value in (*left, *right)):
        raise SemanticSearchUnavailable('Embedding contained non-numeric values')
    if not all(math.isfinite(value) for value in (*left, *right)):
        raise SemanticSearchUnavailable('Embedding contained non-finite values')
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        raise SemanticSearchUnavailable('Embedding had zero magnitude')
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def semantic_search_source(document_id: str, text: str, chapters: list[Chapter], chapter_ids: list[str],
                           query: str, limit: int, api_key: str, model: str,
                           *, client_factory=OpenAI) -> SourceSearchResults:
    selected = resolve_chapters(text, chapters, chapter_ids)
    candidates = _candidates(text, selected)
    if not candidates:
        return SourceSearchResults(document_id=document_id, query=query, matches=[], has_more=False,
                                   match_mode='semantic_embedding')
    inputs = [query, *(text[item.start:item.end] for item in candidates)]
    try:
        with client_factory(api_key=api_key, timeout=20.0, max_retries=1) as client:
            response = client.embeddings.create(model=model, input=inputs, encoding_format='float')
        vectors = [list(item.embedding) for item in response.data]
    except Exception as error:
        raise SemanticSearchUnavailable('Semantic source lookup failed') from error
    if len(vectors) != len(inputs):
        raise SemanticSearchUnavailable('Embedding response count did not match')
    ranked = sorted(((_similarity(vectors[0], vector), candidate)
                     for candidate, vector in zip(candidates, vectors[1:], strict=True)),
                    key=lambda item: (-item[0], item[1].start))
    qualifying = [candidate for score, candidate in ranked if score >= MIN_SIMILARITY]
    chosen = sorted(qualifying[:limit], key=lambda item: item.start)
    matches = [SourceSearchHit(chapter_id=item.chapter.id, title=item.chapter.title,
        start_character=item.start, end_character=item.end,
        text=text[item.start:item.end], match_start=item.start, match_end=item.end,
        context_truncated=item.truncated) for item in chosen]
    return SourceSearchResults(document_id=document_id, query=query, matches=matches,
                               has_more=len(qualifying) > limit, match_mode='semantic_embedding')
