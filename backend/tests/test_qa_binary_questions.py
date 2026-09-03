from pathlib import Path
import subprocess
import sys

import pytest

from app.schemas import Chapter
from scripts.qa_binary_questions import generate_binary_fixture


@pytest.mark.parametrize('kind,options', [('true_false', ['True', 'False']), ('yes_no', ['Yes', 'No'])])
def test_binary_fixture_is_labeled_and_never_needs_provider_settings(kind, options):
    items = generate_binary_fixture('Synthetic source.',
        [Chapter(id='qa', title='QA', start_character=0, end_character=17, confidence=1)],
        ['qa'], 5, None, question_type=kind)
    assert len(items) == 5
    assert all(item.prompt.startswith('QA fixture') for item in items)
    assert all(item.options == options for item in items)
    assert [item.correct_option for item in items] == [options[i % 2] for i in range(5)]


def test_fixture_does_not_fall_back_for_unsupported_format():
    with pytest.raises(ValueError):
        generate_binary_fixture('', [], [], 5, None)


def test_binary_server_still_requires_explicit_qa_flag():
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'serve_qa.py'
    result = subprocess.run([sys.executable, str(script), '--binary-fixtures'],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert 'supply --qa-only' in result.stderr
