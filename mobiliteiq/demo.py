"""Données explicitement synthétiques, réservées à mobiliteiq_demo."""
from datetime import timedelta
import random
import uuid
from .core import utcnow
from .__main__ import ingest, build

def seed(c,cfg):
    if c.info.dbname!='mobiliteiq_demo': raise ValueError('Base de démonstration obligatoire')
    if c.execute('SELECT count(*) FROM runs').fetchone()[0]:
        raise ValueError('Démo déjà initialisée. Elle est conservée; utilisez train, score et export.')
    rng=random.Random(42); now=utcnow().replace(minute=0,second=0,microsecond=0)
    def feature(ident,lon,lat,props):
        return dict(type='Feature',id=ident,geometry={'type':'Point','coordinates':[lon,lat]},properties=props)
    datasets={s:[] for s in cfg['sources']}
    for i in range(6):
        lon=-71.55+i*0.08; lat=46.8
        datasets['travaux'].append(feature(f'T{i}',lon,lat,{'route':f'AXE-DEMO-{i}','start':(now-timedelta(days=2)).isoformat(),'end':None}))
        datasets['rtss'].append(feature(f'R{i}',lon,lat,{'route':f'AXE-DEMO-{i}'}))
        datasets['debit'].append(feature(f'D{i}',lon,lat,{'djma':20000+i*10000,'route':f'AXE-DEMO-{i}'}))
        datasets['meteo'].append(feature(f'M{i}',lon,lat,{'time':now.isoformat(),'temp':10,'precip':0,'wind':15}))
    for source in ['rtss','debit','meteo','travaux']:
        fields={'id':'@id'}
        for k in datasets[source][0]['properties']: fields[k]=k
        ingest(c,source,{'validated':True,'fields':fields},cfg['bbox'],now,
               fetch=lambda s,*args:(datasets[s],'SYNTHETIQUE'))
    build(c,now,cfg['bbox'])
    sectors=[r[0] for r in c.execute('SELECT DISTINCT sector FROM sector_hour')]
    with c.transaction():
        for h in range(30*24):
            hour=now-timedelta(hours=30*24-h)
            for i,sec in enumerate(sectors):
                n=rng.randint(0,5)+(8 if h>680 and i==0 else 0)
                c.execute('INSERT INTO sector_hour VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                          (hour,sec,n,20000+i*10000,8+rng.gauss(0,4),max(0,rng.gauss(0,2)),max(0,rng.gauss(15,5)),1,None))
    print('Démo synthétique créée : 30 jours. Aucun historique réel reconstitué.')
