"""Collecte continue, calendrier persistant dans PostgreSQL."""
import logging
import signal
import threading
from datetime import timedelta

LOG = logging.getLogger(__name__)
ORDER = ('rtss', 'debit', 'meteo', 'travaux')


def due(last, cfg, now):
    if last is None:
        return True
    started, status = last
    minutes = cfg['interval_minutes'] if status == 'success' else cfg.get('retry_minutes', 5)
    if minutes <= 0:
        raise ValueError('Les intervalles doivent Ãªtre positifs')
    if status == 'success' and cfg.get('schedule_mode') == 'calendar':
        # Créneaux UTC : une exécution retardée ne saute pas l'heure suivante.
        seconds = minutes * 60
        return int(now.timestamp() // seconds) > int(started.timestamp() // seconds)
    return now >= started + timedelta(minutes=minutes)


def cycle(c, cfg):
    from .__main__ import ingest, build, monitor
    from .core import utcnow
    # Verrou commun au CLI : aucune publication concurrente.
    if not c.execute('SELECT pg_try_advisory_lock(894210)').fetchone()[0]:
        LOG.info('Traitement dÃ©jÃ  en cours; prochain passage dans une minute')
        return
    try:
        now = utcnow()
        changed = False
        # Le verrou est acquis : tout ancien running appartient Ã  un processus arrÃªtÃ©.
        c.execute("UPDATE runs SET status='failed_source',error='Traitement interrompu avant publication' WHERE status='running'")
        for source in ORDER:
            s = cfg['sources'][source]
            last = c.execute('SELECT started_at,status FROM runs WHERE source=%s ORDER BY started_at DESC LIMIT 1', (source,)).fetchone()
            if due(last, s, now):
                changed = ingest(c, source, s, cfg['bbox'], utcnow()) or changed
        if changed:
            build(c, utcnow(), cfg['bbox'])
        monitor(c, cfg, utcnow())
    finally:
        c.execute('SELECT pg_advisory_unlock(894210)')


def serve(cfg, db=None):
    from .__main__ import connect, init
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    LOG.info('Service de collecte dÃ©marrÃ©; contrÃ´le du calendrier toutes les 60 secondes')
    while not stop.is_set():
        try:
            with connect(db) as c:
                init(c)
                cycle(c, cfg)
        except Exception:
            LOG.exception('Cycle interrompu; nouvelle connexion au prochain passage')
        stop.wait(60)
    LOG.info('Service arrÃªtÃ©')
