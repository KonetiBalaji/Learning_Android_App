import ast
from pathlib import Path

from app.ai_limits import (DIAGNOSTIC_GENERATION_OUTPUT_TOKENS,
                           DOCUMENT_GENERATION_OUTPUT_TOKENS,
                           REVIEW_OUTPUT_TOKENS, TUTOR_OUTPUT_TOKENS)


def test_every_provider_response_has_an_explicit_output_ceiling():
    app_dir = Path(__file__).parents[1] / 'app'
    calls = []
    for path in app_dir.glob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'create' and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == 'responses'):
                calls.append((path.name, node.lineno, {word.arg for word in node.keywords}))
    assert len(calls) == 12
    assert all('max_output_tokens' in keywords for _, _, keywords in calls), calls


def test_provider_output_ceilings_are_positive_and_bounded():
    assert 0 < TUTOR_OUTPUT_TOKENS <= REVIEW_OUTPUT_TOKENS
    assert REVIEW_OUTPUT_TOKENS <= DIAGNOSTIC_GENERATION_OUTPUT_TOKENS
    assert DIAGNOSTIC_GENERATION_OUTPUT_TOKENS <= DOCUMENT_GENERATION_OUTPUT_TOKENS <= 16_384
