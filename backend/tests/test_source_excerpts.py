import pytest

from app.source_excerpts import excerpt_bounds, selected_quote


def test_contiguous_selection_preserves_original_whitespace():
    text = 'First evidence sentence.  Second evidence sentence.\nThird evidence sentence.'
    bounds = excerpt_bounds(text)
    assert len(bounds) == 3
    assert selected_quote(text, bounds, 0, 2) == text
    assert selected_quote(text, bounds, 1, 2) == text[bounds[1][0]:]


def test_long_source_chunks_cover_every_character_without_inventing_text():
    text = 'x' * 2100
    bounds = excerpt_bounds(text)
    assert bounds == [(0, 1000), (1000, 2000), (2000, 2100)]
    assert ''.join(text[start:end] for start, end in bounds) == text
    with pytest.raises(ValueError):
        selected_quote(text, bounds, 0, 2)


@pytest.mark.parametrize('first,last', [(-1, 0), (1, 0), (0, 2)])
def test_invalid_range_is_rejected(first, last):
    text = 'A sufficiently long evidence sentence.'
    with pytest.raises(ValueError):
        selected_quote(text, excerpt_bounds(text), first, last)


def test_empty_and_short_evidence_cannot_pass():
    assert excerpt_bounds('') == []
    with pytest.raises(ValueError):
        selected_quote('Short.', excerpt_bounds('Short.'), 0, 0)
