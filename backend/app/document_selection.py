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
