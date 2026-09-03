"""Number source excerpts so models select evidence instead of transcribing it."""
import re


def excerpt_bounds(text: str) -> list[tuple[int, int]]:
    result = []
    start = 0
    for boundary in re.finditer(r'(?<=[.!?])\s+|\n+', text):
        end = boundary.start()
        while start < end:
            stop = min(start + 1000, end)
            result.append((start, stop))
            start = stop
        start = boundary.end()
    while start < len(text):
        stop = min(start + 1000, len(text))
        result.append((start, stop))
        start = stop
    return result


def selected_quote(text: str, bounds: list[tuple[int, int]], first: int, last: int) -> str:
    if not 0 <= first <= last < len(bounds):
        raise ValueError('Invalid evidence selection')
    quote = text[bounds[first][0]:bounds[last][1]]
    if not 15 <= len(quote) <= 1500:
        raise ValueError('Invalid evidence selection')
    return quote
