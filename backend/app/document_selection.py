"""Resolve the complete requested selection without silently dropping any IDs."""
from .schemas import Chapter


def resolve_chapters(text: str, chapters: list[Chapter], selected_ids: list[str]) -> list[Chapter]:
    if not selected_ids or len(set(selected_ids)) != len(selected_ids):
        raise ValueError('Select one or more distinct chapters')
    by_id = {chapter.id: chapter for chapter in chapters}
    if len(by_id) != len(chapters) or any(identifier not in by_id for identifier in selected_ids):
        raise ValueError('Select valid chapters from this document')
    # Preserve source order, independent of the order in which controls were clicked.
    requested = set(selected_ids)
    selected = [chapter for chapter in chapters if chapter.id in requested]
    for chapter in selected:
        if not 0 <= chapter.start_character < chapter.end_character <= len(text):
            raise ValueError('The selected chapter has an invalid source range')
    for left, right in zip(selected, selected[1:]):
        if left.end_character > right.start_character:
            raise ValueError('The selected chapter ranges overlap or are out of order')
    return selected


def repair_chapter_coverage(text: str, chapters: list[Chapter]) -> list[Chapter]:
    """Fill omitted nonblank source ranges without modifying existing chapters."""
    if chapters:
        resolve_chapters(text, chapters, [chapter.id for chapter in chapters])
    repaired = []
    used = {chapter.id for chapter in chapters}

    def add_gap(start, end):
        if start >= end or not text[start:end].strip():
            return
        identifier = f'recovered-{start}-{end}'
        while identifier in used:
            identifier += '-gap'
        used.add(identifier)
        repaired.append(Chapter(id=identifier, title=f'Previously omitted text (characters {start}-{end})',
                                start_character=start, end_character=end, confidence=0.35))

    position = 0
    for chapter in chapters:
        add_gap(position, chapter.start_character)
        repaired.append(chapter)
        position = chapter.end_character
    add_gap(position, len(text))
    return repaired
