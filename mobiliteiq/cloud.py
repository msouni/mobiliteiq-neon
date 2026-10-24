"""Sélection explicite de la base cloud; aucun repli production pour les tests."""
import os
from psycopg.conninfo import conninfo_to_dict


def connection_options(db=None):
    keys = {'mobiliteiq': 'DATABASE_URL', 'mobiliteiq_demo': 'DATABASE_URL_DEMO',
            'mobiliteiq_test': 'DATABASE_URL_TEST'}
    key = keys.get(db, 'DATABASE_URL')
    url = os.environ.get(key, '').strip()
    cloud = any(os.environ.get(k, '').strip() for k in keys.values())
    if cloud:
        if not url:
            raise ValueError(f'Configurer {key} pour cette base; aucun repli sur la base réelle')
        try:
            opts = conninfo_to_dict(url)
        except Exception:
            raise ValueError('URL PostgreSQL invalide; recopier la connexion directe Neon') from None
        if '-pooler.' in opts.get('host', ''):
            raise ValueError('Utiliser une connexion directe sans -pooler : verrou de session requis')
        expected = db or 'mobiliteiq'
        if opts.get('dbname') != expected:
            raise ValueError(f'La connexion doit cibler exactement {expected}')
        if opts.get('sslmode') not in ('require', 'verify-ca', 'verify-full'):
            raise ValueError('La connexion cloud exige sslmode=require ou une vérification TLS plus stricte')
        return dict(conninfo=url, connect_timeout=30, autocommit=True)
    # CI : PostgreSQL temporaire, sans accès Neon.
    return dict(dbname=db or os.environ.get('PGDATABASE', 'mobiliteiq'),
                connect_timeout=10, autocommit=True)
