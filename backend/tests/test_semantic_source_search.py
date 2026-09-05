from types import SimpleNamespace

import pytest

from app.schemas import Chapter
from app.semantic_source_search import (
    MAX_PASSAGES, MAX_SOURCE_CHARACTERS, SemanticSearchScopeTooLarge, SemanticSearchUnavailable,
    semantic_search_source,
)


def chapter(identifier, start, end):
    return Chapter(id=identifier, title=identifier.title(), start_character=start,
                   end_character=end, confidence=1)


class FakeClient:
    vectors = []
    captured = None

    def __init__(self, **options):
        self.options = options
        self.embeddings = self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def create(self, **request):
        type(self).captured = (self.options, request)
        return SimpleNamespace(data=[SimpleNamespace(embedding=value) for value in self.vectors])


def test_semantic_ranking_returns_verbatim_selected_source_in_source_order():
    first = 'Cars use seat belts to reduce injury.' + ' ' * 1565
    second = 'Plants turn sunlight into stored chemical energy.'
    hidden = 'Automobile safety appears only in the unselected appendix.'
    text = first + '\n' + second + hidden
    allowed_end = len(first) + 1 + len(second)
    chapters = [chapter('allowed', 0, allowed_end), chapter('hidden', allowed_end, len(text))]
    # Query, first passage, second passage. The first is the semantic match even
    # though it contains neither query term.
    FakeClient.vectors = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]
    result = semantic_search_source('doc', text, chapters, ['allowed'], 'automobile protection', 20,
                                    'secret', 'embedding-model', client_factory=FakeClient)
    assert result.match_mode == 'semantic_embedding' and len(result.matches) == 1
    hit = result.matches[0]
    assert hit.chapter_id == 'allowed' and hit.text == text[hit.start_character:hit.end_character]
    assert (hit.match_start, hit.match_end) == (hit.start_character, hit.end_character)
    options, request = FakeClient.captured
    assert options == {'api_key': 'secret', 'timeout': 20.0, 'max_retries': 1}
    assert request['model'] == 'embedding-model' and request['input'][0] == 'automobile protection'
    assert hidden not in ''.join(request['input'])


@pytest.mark.parametrize('vectors', [[], [[1.0]], [[1.0], [1.0, 2.0]],
                                      [[0.0, 0.0], [1.0, 0.0]],
                                      [['invalid', 0.0], [1.0, 0.0]],
                                      [[float('nan'), 0.0], [1.0, 0.0]]])
def test_invalid_embedding_responses_fail_closed(vectors):
    FakeClient.vectors = vectors
    text = 'Source passage'
    with pytest.raises(SemanticSearchUnavailable):
        semantic_search_source('doc', text, [chapter('a', 0, len(text))], ['a'], 'related idea', 1,
                               'secret', 'model', client_factory=FakeClient)


def test_semantic_search_rejects_oversized_scope_before_provider_call():
    text = 'x' * (MAX_SOURCE_CHARACTERS + 1)
    FakeClient.captured = None
    with pytest.raises(SemanticSearchScopeTooLarge, match='select fewer'):
        semantic_search_source('doc', text, [chapter('a', 0, len(text))], ['a'], 'related idea', 1,
                               'secret', 'model', client_factory=FakeClient)
    assert FakeClient.captured is None


def test_semantic_candidates_do_not_join_unrelated_neighboring_paragraphs():
    relevant = 'Plants manufacture stored food by converting light into chemical energy.'
    unrelated = 'This disposable paragraph explains only the mechanics of a QA procedure.'
    text = relevant + '\n\n' + unrelated
    FakeClient.vectors = [[1.0, 0.0], [0.95, 0.05], [0.0, 1.0]]

    result = semantic_search_source('doc', text, [chapter('plants', 0, len(text))], ['plants'],
                                    'plant food production', 1, 'secret', 'model',
                                    client_factory=FakeClient)

    assert len(result.matches) == 1
    assert result.matches[0].text == relevant
    assert result.matches[0].context_truncated is False
    assert unrelated not in result.matches[0].text
    assert FakeClient.captured[1]['input'][1:] == [relevant, unrelated]


def test_long_paragraph_splits_on_sentence_boundary_with_exact_offsets():
    first = ('A' * 390) + '. '
    second = ('B' * 390) + '. '
    third = ('C' * 100) + '.'
    text = first + second + third
    FakeClient.vectors = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]

    result = semantic_search_source('doc', text, [chapter('a', 0, len(text))], ['a'],
                                    'related idea', 1, 'secret', 'model',
                                    client_factory=FakeClient)

    assert FakeClient.captured[1]['input'][1:] == [(first + second).rstrip(), third]
    hit = result.matches[0]
    assert hit.text == text[hit.start_character:hit.end_character] == (first + second).rstrip()
    assert hit.context_truncated is True


def test_semantic_search_rejects_pathologically_fragmented_scope():
    text = '\n\n'.join(f'paragraph {index}' for index in range(MAX_PASSAGES + 1))
    FakeClient.captured = None
    with pytest.raises(SemanticSearchScopeTooLarge, match='too many passages'):
        semantic_search_source('doc', text, [chapter('a', 0, len(text))], ['a'],
                               'related idea', 1, 'secret', 'model', client_factory=FakeClient)
    assert FakeClient.captured is None
