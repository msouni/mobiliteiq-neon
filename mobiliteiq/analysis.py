import json
import uuid
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from psycopg.types.json import Jsonb
from .core import utcnow
from .__main__ import ROOT

CANDIDATES=['n_presentes','djma_max','temp_c','precip_mm','wind_kmh']

def dataframe(c):
    with c.cursor() as cur:
        cur.execute('SELECT * FROM sector_hour ORDER BY hour_utc,sector')
        return pd.DataFrame(cur.fetchall(),columns=[x.name for x in cur.description])

def split_time(df):
    hours=sorted(df.hour_utc.unique())
    if len(hours)<40 or (hours[-1]-hours[0]).total_seconds()<10*86400:
        raise ValueError('Il faut au moins 10 jours et 40 heures distinctes : poursuivre la collecte')
    cutoff=hours[int(len(hours)*0.8)]
    return df[df.hour_utc<cutoff],df[df.hour_utc>=cutoff],cutoff

def execute(c,command):
    df=dataframe(c)
    if df.empty: raise ValueError('Aucune donnée analytique : exécuter demo ou run')
    folder=ROOT/'models'/c.info.dbname; folder.mkdir(parents=True,exist_ok=True)
    if command=='eda':
        out=ROOT/'exports'/c.info.dbname; out.mkdir(parents=True,exist_ok=True)
        df[CANDIDATES].describe().to_csv(out/'statistiques.csv')
        df[CANDIDATES].corr(method='spearman').to_csv(out/'correlations_spearman.csv')
        df[CANDIDATES].isna().mean().rename('taux_manquant').to_csv(out/'manquants.csv')
        print('EDA exportée dans',out); return
    if command=='train':
        train,test,cutoff=split_time(df)
        features=[k for k in CANDIDATES if train[k].notna().mean()>=0.8 and train[k].nunique()>1]
        if not features: raise ValueError('Aucune variable exploitable')
        model=make_pipeline(SimpleImputer(strategy='median'),IsolationForest(n_estimators=200,random_state=42,contamination='auto'))
        model.fit(train[features])
        raw=-model.score_samples(train[features])
        threshold=float(np.quantile(raw,0.97))
        test_scores=-model.score_samples(test[features])
        # Expérience de sensibilité, sans prétendre disposer de véritables anomalies étiquetées.
        injected=test[features].copy()
        if 'n_presentes' in features:
            injected['n_presentes']=float(train.n_presentes.max())*5+20
        sensitivity=float(np.mean(-model.score_samples(injected)>threshold))
        version='iforest-'+utcnow().strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:6]
        med=train[features].median(); mad=(train[features]-med).abs().median().replace(0,1)
        metrics={'train_rows':len(train),'test_rows':len(test),'features':features,'threshold_quantile':0.97,
                 'test_flag_rate':float(np.mean(test_scores>threshold)), 'sensitivity_injected_counts':sensitivity,
                 'sklearn_version':sklearn.__version__,
                 'note':'Aucune précision/rappel réels sans étiquettes. Sensibilité = expérience artificielle; ne mesure pas la performance terrain.'}
        bundle=dict(model=model,features=features,threshold=threshold,cutoff=cutoff,median=med,mad=mad,version=version)
        path=folder/f'{version}.joblib'; joblib.dump(bundle,path)
        c.execute('INSERT INTO models VALUES(%s,%s,%s,%s,%s,%s)',(version,utcnow(),cutoff,threshold,Jsonb(metrics),str(path)))
        print(json.dumps(metrics,indent=2)); execute(c,'score'); return
    row=c.execute('SELECT path FROM models ORDER BY trained_at DESC LIMIT 1').fetchone()
    if not row: raise ValueError('Entraîner un modèle avec train avant score')
    # Charger uniquement les modèles produits localement par ce projet.
    bundle=joblib.load(row[0]); scores=-bundle['model'].score_samples(df[bundle['features']])
    with c.transaction():
        for (_,r),score in zip(df.iterrows(),scores):
            z=((r[bundle['features']].fillna(bundle['median'])-bundle['median'])/bundle['mad']).astype(float)
            strongest=z.abs().idxmax()
            expl=f"Écart principal par rapport à la médiane d'entraînement : {strongest} ({z[strongest]:+.1f} MAD). Indice descriptif, pas une cause."
            phase='train' if r.hour_utc<bundle['cutoff'] else 'evaluation_ou_nouveau'
            c.execute('''INSERT INTO scores(hour_utc,sector,version,score,anomaly,explanation,phase)
            VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(hour_utc,sector,version)
            DO UPDATE SET score=excluded.score,anomaly=excluded.anomaly,explanation=excluded.explanation,computed_at=now()''',
            (r.hour_utc,r.sector,bundle['version'],float(score),bool(score>bundle['threshold']),expl,phase))
    print('Scores sauvegardés :',len(df),'version',bundle['version'])
