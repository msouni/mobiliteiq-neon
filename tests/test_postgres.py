"""Tests réellement PostgreSQL. Sautés uniquement hors environnement de test configuré."""
import os
from datetime import datetime,timezone,timedelta
import pytest
from mobiliteiq.__main__ import connect,init,ingest,build,monitor

@pytest.fixture
def db():
    if os.environ.get('RUN_PG_TESTS')!='1': pytest.skip('Configurer RUN_PG_TESTS=1 et mobiliteiq_test')
    with connect('mobiliteiq_test') as c:
        assert c.info.dbname=='mobiliteiq_test'
        init(c)
        c.execute('TRUNCATE scores,models,sector_hour,rejects,observations,runs,indicators CASCADE')
        yield c

NOW=datetime.now(timezone.utc)
BBOX=[-71.6,46.6,-71,47.1]
CFG={'validated':True,'fields':{'id':'@id'},'interval_minutes':30}
F={'id':'A','type':'Feature','properties':{},'geometry':{'type':'Point','coordinates':[-71.3,46.8]}}

def test_ingestion_history_and_no_duplicate_in_batch(db):
    assert ingest(db,'travaux',CFG,BBOX,NOW,lambda *a:([F,F],'fixture'))
    assert db.execute('SELECT count(*) FROM observations').fetchone()[0]==1
    assert ingest(db,'travaux',CFG,BBOX,NOW+timedelta(minutes=30),lambda *a:([F],'fixture'))
    assert db.execute('SELECT count(*) FROM observations').fetchone()[0]==2
    build(db,NOW+timedelta(minutes=30),BBOX)
    assert db.execute('SELECT count(*) FROM bi.fact_entraves').fetchone()[0]==1

def test_failed_batch_preserves_previous_state(db):
    ingest(db,'travaux',CFG,BBOX,NOW,lambda *a:([F],'fixture'))
    assert not ingest(db,'travaux',CFG,BBOX,NOW+timedelta(minutes=1),lambda *a:([{'id':'B'}],'fixture'))
    assert db.execute('SELECT count(*) FROM bi.fact_entraves').fetchone()[0]==1
    assert db.execute('SELECT count(*) FROM rejects').fetchone()[0]==1

def test_source_failure_is_visible(db):
    def fail(*a): raise TimeoutError('Simulation de panne')
    assert not ingest(db,'travaux',CFG,BBOX,NOW,fail)
    assert monitor(db,{'sources':{'travaux':CFG}},NOW)>0
    assert db.execute('SELECT count(*) FROM bi.ops_alertes').fetchone()[0]>0

def test_uat_manager_can_see_event_and_freshness(db):
    ingest(db,'travaux',CFG,BBOX,NOW,lambda *a:([F],'fixture'))
    build(db,NOW,BBOX);monitor(db,{'sources':{'travaux':CFG}},NOW)
    row=db.execute('SELECT event_id,latitude,longitude FROM bi.fact_entraves').fetchone()
    assert row==('A',46.8,-71.3)
    assert db.execute("SELECT ok FROM bi.ops_indicateurs WHERE name='fraicheur_collecte_min'").fetchone()[0]


def test_continuous_cycle_isolates_failure_and_respects_schedule(db, monkeypatch):
    import mobiliteiq.__main__ as cli
    from mobiliteiq.scheduler import cycle
    from copy import deepcopy
    cfg = {'bbox': BBOX, 'sources': {s: dict(CFG, validation_mode='automatic', validated=False)
                                   for s in ('travaux', 'rtss', 'debit', 'meteo')}}
    cfg['sources']['meteo']['fields'] = {'id': '@id', 'time': 'UTC_DATE'}
    calls = []
    original = cli.ingest
    def fetch(source, *args):
        calls.append(source)
        if source == 'debit':
            raise TimeoutError('Panne simulée')
        feature = deepcopy(F)
        feature['properties']['UTC_DATE'] = NOW.isoformat()
        return [feature], 'fixture'
    monkeypatch.setattr(cli, 'ingest', lambda *args: original(*args, fetch=fetch))
    cycle(db, cfg)
    assert calls == ['rtss', 'debit', 'meteo', 'travaux']
    assert db.execute("SELECT count(*) FROM runs WHERE status='success'").fetchone()[0] == 3
    assert db.execute("SELECT status FROM runs WHERE source='debit'").fetchone()[0] == 'failed_source'
    cycle(db, cfg)
    assert len(calls) == 4  # aucun nouveau téléchargement avant l'échéance
    assert db.execute('SELECT count(*) FROM bi.etat_sources').fetchone()[0] == 4
