import pytest

from scripts.parser_stress_smoke import run


@pytest.mark.parametrize('attempts,concurrency,timeout', [
    (19, 2, 5), (20, 1, 5), (20, 21, 5), (20, 2, 0), (20, 2, 16),
])
def test_parser_stress_rejects_unsafe_bounds(attempts, concurrency, timeout):
    with pytest.raises(ValueError):
        run(attempts, concurrency, timeout)
