CREATE SCHEMA IF NOT EXISTS bi;
CREATE TABLE IF NOT EXISTS runs (
 id text PRIMARY KEY, source text NOT NULL, started_at timestamptz NOT NULL,
 status text NOT NULL, received int DEFAULT 0, accepted int DEFAULT 0,
 rejected int DEFAULT 0, filtered int DEFAULT 0, duplicates int DEFAULT 0,
 duration_s double precision, raw_path text, error text
);
CREATE INDEX IF NOT EXISTS runs_source_time ON runs(source,started_at);
CREATE TABLE IF NOT EXISTS observations (
 run_id text REFERENCES runs(id), source text NOT NULL, item_id text NOT NULL,
 observed_at timestamptz NOT NULL, payload jsonb NOT NULL,
 PRIMARY KEY(run_id,item_id)
);
CREATE TABLE IF NOT EXISTS rejects (
 run_id text REFERENCES runs(id), reason text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS sector_hour (
 hour_utc timestamptz NOT NULL, sector text NOT NULL, n_presentes int NOT NULL,
 djma_max double precision, temp_c double precision, precip_mm double precision,
 wind_kmh double precision, rtss_match_rate double precision, run_id text REFERENCES runs(id),
 PRIMARY KEY(hour_utc,sector)
);
CREATE TABLE IF NOT EXISTS models (
 version text PRIMARY KEY, trained_at timestamptz NOT NULL, cutoff timestamptz NOT NULL,
 threshold double precision NOT NULL, metrics jsonb NOT NULL, path text NOT NULL
);
CREATE TABLE IF NOT EXISTS scores (
 hour_utc timestamptz, sector text, version text REFERENCES models(version),
 score double precision, anomaly boolean, explanation text, phase text,
 computed_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(hour_utc,sector,version)
);
CREATE TABLE IF NOT EXISTS indicators (
 source text, name text, value double precision, threshold double precision,
 ok boolean NOT NULL, computed_at timestamptz DEFAULT now(), PRIMARY KEY(source,name)
);
CREATE OR REPLACE VIEW bi.info_projet AS
SELECT current_database() AS base,
 CASE WHEN current_database() LIKE '%demo' THEN 'DEMONSTRATION SYNTHETIQUE' ELSE 'DONNEES REELLES' END AS mode;
CREATE OR REPLACE VIEW bi.ops_ingestions AS SELECT * FROM runs;
CREATE OR REPLACE VIEW bi.ops_rejets AS SELECT * FROM rejects;
CREATE OR REPLACE VIEW bi.ops_indicateurs AS SELECT * FROM indicators;
CREATE OR REPLACE VIEW bi.ops_alertes AS SELECT * FROM indicators WHERE NOT ok;
CREATE OR REPLACE VIEW bi.fact_entraves AS
SELECT o.item_id AS event_id,r.started_at AS collecte_utc,
 o.payload->>'route' AS axe,o.payload->>'sector' AS sector,
 (o.payload->>'lon')::float AS longitude,(o.payload->>'lat')::float AS latitude,
 (o.payload->>'start')::timestamptz AS debut_source,
 (o.payload->>'end')::timestamptz AS fin_source,
 (SELECT min(r2.started_at) FROM observations o2 JOIN runs r2 ON r2.id=o2.run_id
 WHERE o2.source='travaux' AND r2.status='success' AND o2.item_id=o.item_id) AS premiere_observation_utc
FROM observations o JOIN runs r ON r.id=o.run_id
WHERE r.id=(SELECT id FROM runs WHERE source='travaux' AND status='success' ORDER BY started_at DESC LIMIT 1);
CREATE OR REPLACE VIEW bi.fact_secteur_heure AS
SELECT h.*, (h.hour_utc AT TIME ZONE 'America/Toronto')::date AS date_key,
 h.hour_utc AT TIME ZONE 'America/Toronto' AS heure_locale,
 s.version,s.score,s.anomaly,s.explanation,s.phase
FROM sector_hour h LEFT JOIN scores s ON s.hour_utc=h.hour_utc AND s.sector=h.sector
 AND s.version=(SELECT version FROM models ORDER BY trained_at DESC LIMIT 1);
CREATE OR REPLACE VIEW bi.dim_secteur AS SELECT DISTINCT sector FROM sector_hour;
CREATE OR REPLACE VIEW bi.dim_date AS
SELECT DISTINCT (hour_utc AT TIME ZONE 'America/Toronto')::date AS date_key FROM sector_hour;
CREATE OR REPLACE VIEW bi.modeles AS SELECT * FROM models;
-- Durée réellement observée dans nos collectes, pas durée officielle du chantier.
CREATE OR REPLACE VIEW bi.historique_entraves AS
WITH h AS (
 SELECT o.item_id AS event_id,min(r.started_at) AS premiere_observation_utc,
        max(r.started_at) AS derniere_observation_utc,count(*) AS nombre_observations,
        (array_agg(o.payload->>'route' ORDER BY r.started_at DESC))[1] AS axe,
        (array_agg(o.payload->>'sector' ORDER BY r.started_at DESC))[1] AS sector
 FROM observations o JOIN runs r ON r.id=o.run_id
 WHERE o.source='travaux' AND r.status='success' GROUP BY o.item_id
)
SELECT h.*,extract(epoch FROM (derniere_observation_utc-premiere_observation_utc))/3600 AS duree_observee_h,
 EXISTS(SELECT 1 FROM bi.fact_entraves f WHERE f.event_id=h.event_id) AS presente_dernier_extrait,
 (premiere_observation_utc AT TIME ZONE 'America/Toronto')::date AS date_key
FROM h;

CREATE OR REPLACE VIEW bi.etat_sources AS
SELECT s.source, r.started_at AS derniere_tentative_utc, r.status,
 r.error, ok.started_at AS derniere_reussite_utc,
 extract(epoch FROM (now()-ok.started_at))/60 AS age_collecte_minutes,
 r.received, r.accepted, r.rejected
FROM (VALUES ('travaux'),('debit'),('rtss'),('meteo')) AS s(source)
LEFT JOIN LATERAL (SELECT * FROM runs WHERE source=s.source ORDER BY started_at DESC LIMIT 1) r ON true
LEFT JOIN LATERAL (SELECT started_at FROM runs WHERE source=s.source AND status='success' ORDER BY started_at DESC LIMIT 1) ok ON true;

CREATE OR REPLACE VIEW bi.observations_courantes AS
SELECT o.source,o.item_id,o.observed_at,r.started_at AS collecte_utc,o.payload
FROM observations o JOIN runs r ON r.id=o.run_id
WHERE r.status='success' AND r.id=(SELECT r2.id FROM runs r2
 WHERE r2.source=o.source AND r2.status='success' ORDER BY r2.started_at DESC LIMIT 1);
