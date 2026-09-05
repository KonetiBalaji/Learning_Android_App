"""Live synthetic holdout for the bounded semantic source-search ranker.

No learner text, credentials, embeddings or provider response bodies are printed.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI

from app.config import get_settings
from app.semantic_source_search import MIN_SIMILARITY, _similarity


CASES = (
    ('transport_safety', 'automobile occupant protection',
     'Cars use seat belts and crumple zones to reduce injury during a collision.',
     ('Plants use chlorophyll to capture light.', 'A noun names a person, place, thing, or idea.')),
    ('plant_energy', 'botanical nutrition production',
     'Photosynthesis lets plants convert sunlight into stored chemical energy and sugars.',
     ('Road signs help drivers navigate safely.', 'Elected representatives debate proposed laws.')),
    ('fractions', 'equal shares of a whole',
     'A fraction represents some of the identical parts into which one complete unit is divided.',
     ('Evaporation changes liquid water into vapor.', 'Verbs express actions or states of being.')),
    ('urbanization', 'movement toward cities for jobs',
     'Urbanization occurs when people relocate from rural communities to urban areas for employment and services.',
     ('Triangles have three sides and three angles.', 'Roots absorb water and dissolved minerals.')),
    ('adjectives', 'describing terms modify naming terms',
     'Adjectives add details to nouns by expressing qualities such as size, color, number, or condition.',
     ('Gravity accelerates objects toward Earth.', 'Citizens vote in periodic elections.')),
    ('liquids', 'material keeps volume but takes container form',
     'Liquids have a definite volume but adopt the shape of the vessel that holds them.',
     ('A paragraph develops one central idea.', 'Percent means a quantity measured out of one hundred.')),
    ('representative_government', 'elected lawmaking delegates',
     'In a representative democracy, citizens choose legislators who make public laws on their behalf.',
     ('Mitochondria release energy for cellular work.', 'Weather describes short-term atmospheric conditions.')),
    ('cell_energy', 'cellular structure releases usable power',
     'Mitochondria transform energy from nutrients into a form that cells can use for their activities.',
     ('A map scale relates map distance to ground distance.', 'An equation states that two expressions are equal.')),
)

NEGATIVE_CASES = (
    ('advanced_physics', 'quantum entanglement experimental evidence',
     ('A fraction represents equal parts of a whole.', 'Plants convert sunlight into stored energy.',
      'Adjectives add detail to nouns.')),
    ('historical_dating', 'medieval manuscript carbon dating',
     ('Liquids adopt the shape of a vessel.', 'People move to cities for employment.',
      'Mitochondria release energy for cells.')),
    ('music_theory', 'jazz harmony improvisation',
     ('Citizens choose legislators in elections.', 'Map scale compares two distances.',
      'Gravity pulls objects toward Earth.')),
    ('geology', 'volcanic magma crystallization',
     ('A paragraph develops a central idea.', 'Percent means out of one hundred.',
      'Representatives debate proposed laws.')),
)


def main() -> int:
    settings = get_settings()
    if settings.ai_mode != 'openai' or not settings.openai_api_key:
        raise SystemExit('Live semantic evaluation requires the configured OpenAI mode')
    inputs = ([value for _, query, expected, distractors in CASES
               for value in (query, expected, *distractors)]
              + [value for _, query, passages in NEGATIVE_CASES for value in (query, *passages)])
    with OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=1) as client:
        response = client.embeddings.create(model=settings.openai_embedding_model,
                                            input=inputs, encoding_format='float')
    vectors = [list(item.embedding) for item in response.data]
    if len(vectors) != len(inputs):
        raise SystemExit('Embedding response count did not match the evaluation input')
    cursor = 0
    results = []
    failures = []
    for label, _query, _expected, distractors in CASES:
        width = 2 + len(distractors)
        query_vector, expected_vector, *distractor_vectors = vectors[cursor:cursor + width]
        cursor += width
        expected_score = _similarity(query_vector, expected_vector)
        distractor_scores = [_similarity(query_vector, value) for value in distractor_vectors]
        best_distractor = max(distractor_scores)
        passed = expected_score >= MIN_SIMILARITY and expected_score > best_distractor
        results.append({'case': label, 'expected_score': round(expected_score, 3),
                        'best_distractor_score': round(best_distractor, 3),
                        'margin': round(expected_score - best_distractor, 3), 'passed': passed})
        if not passed:
            failures.append(label)
    negative_results = []
    for label, _query, passages in NEGATIVE_CASES:
        width = 1 + len(passages)
        query_vector, *passage_vectors = vectors[cursor:cursor + width]
        cursor += width
        best_score = max(_similarity(query_vector, value) for value in passage_vectors)
        passed = best_score < MIN_SIMILARITY
        negative_results.append({'case': label, 'best_score': round(best_score, 3), 'passed': passed})
        if not passed:
            failures.append(f'negative:{label}')
    print(json.dumps({'model': settings.openai_embedding_model, 'threshold': MIN_SIMILARITY,
                      'cases': results, 'positive_passed': sum(item['passed'] for item in results),
                      'negative_passed': sum(item['passed'] for item in negative_results),
                      'negative_cases': negative_results, 'failed': failures}, sort_keys=True))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
