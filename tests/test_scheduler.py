from datetime import datetime, timezone, timedelta
from mobiliteiq.scheduler import due

NOW = datetime(2026, 10, 22, tzinfo=timezone.utc)
CFG = {'interval_minutes': 60, 'retry_minutes': 5}


def test_first_start():
    assert due(None, CFG, NOW)


def test_success_waits_own_interval():
    assert not due((NOW, 'success'), CFG, NOW + timedelta(minutes=59))
    assert due((NOW, 'success'), CFG, NOW + timedelta(minutes=60))


def test_failure_retries_without_waiting_daily_interval():
    for status in ('failed_quality', 'failed_source'):
        assert not due((NOW, status), CFG, NOW + timedelta(minutes=4))
        assert due((NOW, status), CFG, NOW + timedelta(minutes=5))


def test_restart_uses_persisted_timestamp():
    assert due((NOW - timedelta(days=2), 'success'), CFG, NOW)
