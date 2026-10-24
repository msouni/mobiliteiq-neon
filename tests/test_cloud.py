import pytest
from mobiliteiq.cloud import connection_options
from mobiliteiq.scheduler import due
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    for key in ('DATABASE_URL', 'DATABASE_URL_DEMO', 'DATABASE_URL_TEST'):
        monkeypatch.delenv(key, raising=False)


def test_cloud_requires_tls(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:secret@host/mobiliteiq')
    with pytest.raises(ValueError, match='sslmode'):
        connection_options()


def test_direct_url(monkeypatch):
    url = 'postgresql://user:secret@ep-example.aws.neon.tech/mobiliteiq?sslmode=require'
    monkeypatch.setenv('DATABASE_URL', url)
    assert connection_options()['conninfo'] == url
    assert connection_options()['autocommit']


def test_no_test_fallback_to_production(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:secret@host/mobiliteiq?sslmode=require')
    with pytest.raises(ValueError, match='DATABASE_URL_TEST'):
        connection_options('mobiliteiq_test')


def test_wrong_database_rejected(monkeypatch):
    monkeypatch.setenv('DATABASE_URL_TEST', 'postgresql://user:secret@host/mobiliteiq?sslmode=require')
    with pytest.raises(ValueError, match='mobiliteiq_test'):
        connection_options('mobiliteiq_test')


def test_session_lock_requires_direct_host(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:secret@ep-a-pooler.aws.neon.tech/mobiliteiq?sslmode=require')
    with pytest.raises(ValueError, match='directe'):
        connection_options()


def test_ci_without_cloud():
    assert connection_options('mobiliteiq_test')['dbname'] == 'mobiliteiq_test'


def test_hourly_calendar_handles_delayed_previous_job():
    last = datetime(2026, 10, 22, 9, 22, tzinfo=timezone.utc)
    now = datetime(2026, 10, 22, 10, 17, tzinfo=timezone.utc)
    assert due((last, 'success'), {'interval_minutes': 60, 'schedule_mode': 'calendar'}, now)
