import pytest

from scripts.production_load_smoke import percentile, run


def test_percentile_uses_nearest_rank_without_underreporting_tail():
    values = [0.01, 0.02, 0.03, 0.04, 0.50]
    assert percentile(values, 50) == 0.03
    assert percentile(values, 95) == 0.50


@pytest.mark.parametrize(('requests', 'concurrency'), [
    (19, 2), (5001, 2), (20, 1), (20, 101), (20, 21),
])
def test_load_shape_is_bounded_before_any_network_request(requests, concurrency):
    with pytest.raises(ValueError, match='20-5000 requests'):
        run('http://127.0.0.1:1', requests, concurrency)
