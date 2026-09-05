import re

from scripts.evaluate_semantic_retrieval import CASES, NEGATIVE_CASES


def meaningful_words(value):
    return {word for word in re.findall(r'[a-z]+', value.lower())
            if len(word) > 3 and word not in {'into', 'from', 'that', 'them', 'their', 'they', 'with'}}


def test_live_semantic_cases_are_unique_and_require_more_than_literal_matching():
    labels = [label for label, *_ in CASES]
    assert len(labels) == len(set(labels)) >= 8
    for _label, query, expected, distractors in CASES:
        assert not (meaningful_words(query) <= meaningful_words(expected))
        assert len(distractors) >= 2
        assert expected not in distractors


def test_live_semantic_negative_cases_are_unique_and_bounded():
    labels = [label for label, *_ in NEGATIVE_CASES]
    assert len(labels) == len(set(labels)) >= 4
    assert all(len(passages) >= 3 for _label, _query, passages in NEGATIVE_CASES)
