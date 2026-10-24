from datetime import datetime,timezone,timedelta
import pandas as pd
import pytest
from mobiliteiq.core import normalize,date,nearest
from mobiliteiq.analysis import split_time

NOW=datetime(2026,1,1,tzinfo=timezone.utc)
BBOX=[-71.6,46.6,-71,47.1]
def f(coords=None,properties=None):
    return {'id':'X','geometry':{'type':'Point','coordinates':coords or [-71.3,46.8]},'properties':properties or {}}

def test_normalize_and_missing_id():
    assert normalize(f(),'travaux',{'id':'@id'},BBOX,NOW)['id']=='X'
    x=f();del x['id']
    with pytest.raises(ValueError): normalize(x,'travaux',{'id':'@id'},BBOX,NOW)

def test_geography():
    assert normalize(f([-73,45]),'travaux',{'id':'@id'},BBOX,NOW) is None
    with pytest.raises(ValueError): normalize(f([400,46]),'travaux',{'id':'@id'},BBOX,NOW)

def test_schema_change_fails():
    with pytest.raises(ValueError,match='absent'): normalize(f(),'debit',{'id':'@id','djma':'DJMA'},BBOX,NOW)

def test_dates_are_not_silently_local():
    with pytest.raises(ValueError): date('2026-01-01T12:00:00')
    assert date('2026-01-01T12:00:00-05:00').hour==17

def test_bad_numeric_value():
    with pytest.raises(ValueError): normalize(f(properties={'d':-1}),'debit',{'id':'@id','djma':'d'},BBOX,NOW)

def test_spatial_threshold():
    e=normalize(f(),'travaux',{'id':'@id'},BBOX,NOW)
    r=normalize(f([-71.31,46.8]),'rtss',{'id':'@id'},BBOX,NOW)
    assert nearest(e,[r],250) is None
    assert nearest(e,[r],2000)['id']=='X'

def test_temporal_split_no_shared_hour():
    df=pd.DataFrame({'hour_utc':[NOW+timedelta(hours=i) for i in range(300) for _ in range(2)]})
    tr,te,cutoff=split_time(df)
    assert tr.hour_utc.max()<te.hour_utc.min()
    assert len(tr)+len(te)==len(df)

def test_geomet_utc_without_suffix():
    x=f(properties={'UTC_DATE':'2026-01-01T12:00:00'})
    r=normalize(x,'meteo',{'id':'@id','time':'UTC_DATE'},BBOX,NOW)
    assert date(r['observed_at']).hour==12
