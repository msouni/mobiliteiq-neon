from datetime import datetime, timezone
import math
from shapely.geometry import shape, box, mapping
from shapely import transform
from pyproj import Transformer

UTC = timezone.utc
PROJECT = Transformer.from_crs(4326, 32187, always_xy=True).transform

def utcnow():
    return datetime.now(UTC)

def date(value):
    if value in (None, ''):
        return None
    d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Date sans fuseau : documenter et convertir la source en UTC')
    return d.astimezone(UTC)

def number(value):
    if value in (None, ''):
        return None
    v = float(value)
    if not math.isfinite(v):
        raise ValueError('Nombre non fini')
    return v

def sector(lon, lat, bbox):
    # Grille pédagogique de 0,1 degré; ce ne sont pas des quartiers officiels.
    return f'S{math.floor((lon-bbox[0])/0.1):02d}_{math.floor((lat-bbox[1])/0.1):02d}'

def normalize(feature, source, fields, bbox, now):
    p = feature.get('properties') or {}
    def get(name):
        field = fields.get(name)
        if field == '@id':
            return feature.get('id')
        if field is None:
            return None
        if field not in p:
            raise ValueError(f'Champ configuré absent : {field}')
        return p[field]
    ident = get('id')
    if ident is None or str(ident).strip() == '':
        raise ValueError('Identifiant source absent')
    g = shape(feature['geometry'])
    if g.is_empty or not g.is_valid:
        raise ValueError('Géométrie vide ou invalide')
    xmin,ymin,xmax,ymax = g.bounds
    if not (-180 <= xmin <= xmax <= 180 and -90 <= ymin <= ymax <= 90):
        raise ValueError('Coordonnées hors EPSG:4326')
    if not g.intersects(box(*bbox)):
        return None
    pt = g.intersection(box(*bbox)).representative_point()
    time_value = get('time') if source == 'meteo' else None
    # UTC_DATE est explicitement UTC même si GeoMet omet le suffixe Z.
    if source == 'meteo' and fields.get('time') == 'UTC_DATE' and time_value:
        parsed = datetime.fromisoformat(str(time_value).replace('Z', '+00:00'))
        time_value = parsed.replace(tzinfo=UTC).isoformat() if parsed.tzinfo is None else time_value
    obs = date(time_value) if source == 'meteo' else now
    if obs is None:
        raise ValueError('Date météo absente')
    result = dict(id=str(ident), observed_at=obs.isoformat(), lon=pt.x, lat=pt.y,
                  sector=sector(pt.x,pt.y,bbox), geometry=mapping(g), route=get('route'))
    for key in ('djma','temp','precip','wind'):
        result[key] = number(get(key))
    for key in ('djma','precip','wind'):
        if result[key] is not None and result[key] < 0:
            raise ValueError(f'{key} négatif ou code manquant non normalisé')
    for key in ('start','end'):
        d = date(get(key)); result[key] = d.isoformat() if d else None
    if result['start'] and result['end'] and result['end'] < result['start']:
        raise ValueError('Fin avant début')
    return result

def nearest(event, candidates, max_m):
    g = transform(shape(event['geometry']), PROJECT, interleaved=False)
    best, distance = None, float('inf')
    for c in candidates:
        d = g.distance(transform(shape(c['geometry']), PROJECT, interleaved=False))
        if d < distance:
            best,distance = c,d
    return best if distance <= max_m else None
