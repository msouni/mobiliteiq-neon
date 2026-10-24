-- À exécuter dans mobiliteiq après création du rôle powerbi_reader.
GRANT CONNECT ON DATABASE mobiliteiq TO powerbi_reader;
GRANT USAGE ON SCHEMA bi TO powerbi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA bi TO powerbi_reader;
-- Exécuter sous le propriétaire qui crée les vues.
ALTER DEFAULT PRIVILEGES IN SCHEMA bi GRANT SELECT ON TABLES TO powerbi_reader;
