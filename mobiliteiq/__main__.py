"""CLI explicite : audit -> init-db -> run -> train -> score -> monitor."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from datetime import timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg
from psycopg.types.json import Jsonb
from .core import utcnow, normalize, nearest, date

ROOT = Path(__file__).resolve().parents[1]

def settings():
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                k,v = line.split('=',1); os.environ.setdefault(k.strip(),v.strip())
    return json.loads((ROOT/'config/sources.json').read_text())

def connect(db=None):
    from .cloud import connection_options
    return psycopg.connect(**connection_options(db))


def init(c):
    c.execute((ROOT/'sql/schema.sql').read_text())

def download(source, cfg, bbox, now):
    session = requests.Session()
    session.mount('https://',HTTPAdapter(max_retries=Retry(total=2,backoff_factor=1,
                    status_forcelist=[429,500,502,503,504],allowed_methods=['GET'])))
    if source == 'meteo':
        url = f"https://api.weather.gc.ca/collections/{cfg['collection']}/items"
        params = {'f':'json','bbox':','.join(map(str,bbox)), 'limit':1000,
                  'datetime':f'{(now-timedelta(days=2)).isoformat()}/{now.isoformat()}'}
    else:
        url = 'https://ws.mapserver.transports.gouv.qc.ca/swtq'
        params = dict(service='WFS',version='2.0.0',request='GetFeature',typeNames=cfg['layer'],
                      outputFormat='geojson',srsName='EPSG:4326',
                      bbox=','.join(map(str,[bbox[1],bbox[0],bbox[3],bbox[2]]))+',EPSG:4326',count=1000,startIndex=0)
    all_features, hashes = [], set()
    for page in range(100):
        response = session.get(url,params=params,timeout=(10,60)); response.raise_for_status()
        raw = response.content
        folder = ROOT/'data/raw'/source/now.strftime('%Y%m%dT%H%M%S%fZ')
        folder.mkdir(parents=True,exist_ok=True)
        with gzip.open(folder/f'{page:03d}.json.gz','wb') as f: f.write(raw)
        (folder/f'{page:03d}.sha256').write_text(hashlib.sha256(raw).hexdigest())
        data = response.json()
        if data.get('type') != 'FeatureCollection' or not isinstance(data.get('features'),list):
            raise ValueError('La réponse ne respecte pas le format GeoJSON FeatureCollection')
        features = data['features']
        if features:
            digest = hashlib.sha256(json.dumps(features,sort_keys=True).encode()).hexdigest()
            if digest in hashes: raise ValueError('Pagination répétée : collecte incomplète refusée')
            hashes.add(digest)
        all_features.extend(features)
        if source == 'meteo':
            nxt = next((l['href'] for l in data.get('links',[]) if l.get('rel')=='next'),None)
            if not nxt: break
            from urllib.parse import urljoin, urlparse
            url = urljoin(url,nxt)
            if urlparse(url).hostname != 'api.weather.gc.ca': raise ValueError('Hôte de pagination inattendu')
            params = None
        else:
            if len(features)<1000: break
            params['startIndex'] += len(features)
    else: raise ValueError('Limite 100 pages : réduire le territoire ou corriger la pagination')
    return all_features,str(folder.relative_to(ROOT))

def ingest(c, source, cfg, bbox, now, fetch=download):
    started=time.monotonic(); rid=uuid.uuid4().hex
    c.execute('INSERT INTO runs(id,source,started_at,status) VALUES(%s,%s,%s,%s)',(rid,source,now,'running'))
    try:
        if cfg.get('validation_mode') != 'automatic' and not cfg.get('validated'):
            raise ValueError('Audit des champs non validé dans config/sources.json')
        features,raw_path=fetch(source,cfg,bbox,now)
        accepted, rejected, filtered, duplicates = {},[],0,0
        for f in features:
            try:
                r=normalize(f,source,cfg['fields'],bbox,now)
                if r is None: filtered+=1
                elif r['id'] in accepted: duplicates+=1
                else: accepted[r['id']]=r
            except (ValueError,TypeError,KeyError) as e: rejected.append((str(e),f))
        # Une source vide peut être normale pour les travaux. Un schéma entièrement
        # invalide ne doit jamais effacer le dernier état valide.
        bad = bool(rejected) and len(rejected)/max(1,len(features)-filtered)>0.1
        if source!='travaux' and not accepted: bad=True
        with c.transaction():
            for reason,f in rejected:
                c.execute('INSERT INTO rejects VALUES(%s,%s,%s)',(rid,reason,Jsonb(f)))
            if not bad:
                for r in accepted.values():
                    c.execute('INSERT INTO observations VALUES(%s,%s,%s,%s,%s)',
                              (rid,source,r['id'],r['observed_at'],Jsonb(r)))
            c.execute('UPDATE runs SET status=%s,received=%s,accepted=%s,rejected=%s,filtered=%s,duplicates=%s,duration_s=%s,raw_path=%s,error=%s WHERE id=%s',
                      ('failed_quality' if bad else 'success',len(features),0 if bad else len(accepted),len(rejected),filtered,duplicates,
                       time.monotonic()-started,raw_path,'Qualité insuffisante : lot non publié' if bad else None,rid))
        print(source, 'failed_quality' if bad else 'success', 'reçues=',len(features),'acceptées=',0 if bad else len(accepted))
        return not bad
    except Exception as e:
        # Ne pas enregistrer les chaînes de connexion dans les journaux.
        message=f'{type(e).__name__}: {str(e)[:350]}'
        c.execute('UPDATE runs SET status=%s,error=%s,duration_s=%s WHERE id=%s',('failed_source',message,time.monotonic()-started,rid))
        print(source,message); return False

def latest(c,source,at):
    r=c.execute("SELECT id,started_at FROM runs WHERE source=%s AND status='success' AND started_at<=%s ORDER BY started_at DESC LIMIT 1",(source,at)).fetchone()
    if not r: return None,[]
    return r,list(x[0] for x in c.execute('SELECT payload FROM observations WHERE run_id=%s',(r[0],)).fetchall())

def build(c,now,bbox):
    run,work=latest(c,'travaux',now)
    if not run: return
    # Ne pas inventer des observations lors d'une panne : l'heure provient du lot valide.
    hour=run[1].replace(minute=0,second=0,microsecond=0)
    ref,roads=latest(c,'rtss',run[1]); dr,traffic=latest(c,'debit',run[1]); mr,weather=latest(c,'meteo',run[1])
    if ref and run[1]-ref[1]>timedelta(days=3): roads=[]
    if dr and run[1]-dr[1]>timedelta(days=3): traffic=[]
    # Dernière observation disponible à l'heure du chantier, au plus 3 heures ancienne.
    weather=[w for w in weather if timedelta(0)<=run[1]-date(w['observed_at'])<=timedelta(hours=3)]
    by_station={}
    for w in sorted(weather,key=lambda x:x['observed_at']):
        by_station[(w['lon'],w['lat'])]=w
    weather=list(by_station.values())
    groups={}
    for w in work: groups.setdefault(w['sector'],[]).append(w)
    # Inclure les secteurs connus sans entrave dans un instantané réussi (zéro observé).
    for (sec,) in c.execute('SELECT DISTINCT sector FROM sector_hour').fetchall(): groups.setdefault(sec,[])
    with c.transaction():
        # Un nouveau lot dans la même heure rend les anciens scores de cette heure caducs.
        c.execute('DELETE FROM scores WHERE hour_utc=%s',(hour,))
        for sec,events in groups.items():
            ds=[]; matches=0; temperatures=[]; precip=[]; winds=[]
            for e in events:
                r=nearest(e,roads,250); t=nearest(e,traffic,250); m=nearest(e,weather,50000)
                matches+=int(r is not None)
                if t and t['djma'] is not None: ds.append(t['djma'])
                if m:
                    for k,ls in [('temp',temperatures),('precip',precip),('wind',winds)]:
                        if m[k] is not None: ls.append(m[k])
            avg=lambda a:sum(a)/len(a) if a else None
            c.execute('''INSERT INTO sector_hour VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(hour_utc,sector) DO UPDATE SET n_presentes=excluded.n_presentes,
            djma_max=excluded.djma_max,temp_c=excluded.temp_c,precip_mm=excluded.precip_mm,
            wind_kmh=excluded.wind_kmh,rtss_match_rate=excluded.rtss_match_rate,run_id=excluded.run_id''',
            (hour,sec,len(events),max(ds) if ds else None,avg(temperatures),avg(precip),avg(winds),matches/len(events) if events else None,run[0]))

def monitor(c,cfg,now):
    alerts=0
    with c.transaction():
        for source,s in cfg['sources'].items():
            rows=c.execute('SELECT started_at,status,received,rejected FROM runs WHERE source=%s ORDER BY started_at DESC LIMIT 100',(source,)).fetchall()
            successful=next((r for r in rows if r[1]=='success'),None)
            age=(now-successful[0]).total_seconds()/60 if successful else None
            streak=0
            for r in rows:
                if r[1]=='success': break
                streak+=1
            rate=rows[0][3]/max(rows[0][2],1) if rows else None
            vals=[('fraicheur_collecte_min',age, s['interval_minutes']*2.5,age is not None and age<=s['interval_minutes']*2.5),
                  ('echecs_consecutifs',streak,3,streak<3),('taux_rejet',rate,0.1,rate is not None and rate<=0.1)]
            if source=='meteo':
                rr,ws=latest(c,source,now)
                obs=max((date(w['observed_at']) for w in ws),default=None)
                lag=(now-obs).total_seconds()/3600 if obs else None
                vals.append(('age_observation_meteo_h',lag,3,lag is not None and 0<=lag<=3))
            for name,value,threshold,ok in vals:
                alerts+=int(not ok)
                c.execute('''INSERT INTO indicators VALUES(%s,%s,%s,%s,%s,%s)
                ON CONFLICT(source,name) DO UPDATE SET value=excluded.value,threshold=excluded.threshold,ok=excluded.ok,computed_at=excluded.computed_at''',
                          (source,name,value,threshold,ok,now))
    print('ALERTES OUVERTES :',alerts)
    return alerts

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--db',choices=['mobiliteiq','mobiliteiq_demo','mobiliteiq_test'])
    ap.add_argument('command',choices=['check-db','init-db','audit','run','demo','train','score','monitor','export','eda','serve'])
    ap.add_argument('--force',action='store_true'); a=ap.parse_args(); cfg=settings(); now=utcnow()
    if a.command=='serve':
        from .scheduler import serve
        serve(cfg, a.db)
        return
    if a.command=='audit':
        out={}
        for source,s in cfg['sources'].items():
            try:
                fs,path=download(source,s,cfg['bbox'],now)
                out[source]={'count':len(fs),'raw_path':path,'examples':fs[:2],
                             'fields':sorted(set().union(*(f.get('properties',{}).keys() for f in fs)))}
            except Exception as e: out[source]={'error':str(e)}
        folder=ROOT/'data'; folder.mkdir(exist_ok=True)
        (folder/'audit.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
        print('Lire data/audit.json; les données brutes sont conservées.'); return
    with connect(a.db) as c:
        if a.command=='check-db':
            print('Connexion réussie :', c.info.dbname)
            print('Chiffrement TLS :', bool(c.pgconn.ssl_in_use))
            return
        init(c)
        if not c.execute('SELECT pg_try_advisory_lock(894210)').fetchone()[0]:
            raise SystemExit('Un autre traitement MobiliteIQ est déjà en cours')
        if a.command=='init-db': print('Base et vues prêtes'); return
        if a.command=='demo':
            if c.info.dbname!='mobiliteiq_demo': raise SystemExit('La démo exige --db mobiliteiq_demo')
            from .demo import seed
            seed(c,cfg); return
        if a.command=='run':
            from .scheduler import due
            c.execute("UPDATE runs SET status='failed_source',error='Traitement interrompu avant publication' WHERE status='running'")
            good=True; changed=False
            for source in ['rtss','debit','meteo','travaux']:
                s=cfg['sources'][source]
                previous=c.execute('SELECT started_at,status FROM runs WHERE source=%s ORDER BY started_at DESC LIMIT 1',(source,)).fetchone()
                if a.force or due(previous,s,utcnow()):
                    ok=ingest(c,source,s,cfg['bbox'],utcnow())
                    good=ok and good; changed=changed or ok
            if changed: build(c,utcnow(),cfg['bbox'])
            monitor(c,cfg,utcnow())
            if not good: raise SystemExit(1)
        elif a.command=='monitor':
            if monitor(c,cfg,now): raise SystemExit(2)
        elif a.command in ('train','score','eda'):
            from .analysis import execute
            execute(c,a.command)
        elif a.command=='export':
            out=ROOT/'exports'/c.info.dbname; out.mkdir(parents=True,exist_ok=True)
            for (view,) in c.execute("SELECT table_name FROM information_schema.views WHERE table_schema='bi'").fetchall():
                from psycopg import sql
                with (out/f'{view}.csv').open('wb') as f:
                    with c.cursor().copy(sql.SQL('COPY (SELECT * FROM bi.{}) TO STDOUT WITH CSV HEADER').format(sql.Identifier(view))) as cp:
                        for block in cp: f.write(block)
            print(out)

if __name__=='__main__':
    main()
