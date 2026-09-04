import pytest

from app.serve import configured_workers


def test_server_defaults_to_one_worker_and_accepts_bounded_concurrency(monkeypatch):
    monkeypatch.delenv('LEARNING_WEB_CONCURRENCY', raising=False)
    assert configured_workers() == 1
    assert configured_workers('2', platform_name='posix') == 2
    assert configured_workers('8', platform_name='posix') == 8


@pytest.mark.parametrize('value', ['0', '9', '-1', 'two', '', '1.5'])
def test_server_rejects_unsafe_worker_configuration(value):
    with pytest.raises(ValueError, match='integer from 1 to 8'):
        configured_workers(value)


def test_multiple_workers_fail_fast_on_windows():
    with pytest.raises(ValueError, match='Linux production container'):
        configured_workers('2', platform_name='nt')
