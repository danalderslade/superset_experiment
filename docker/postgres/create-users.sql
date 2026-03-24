-- PostgreSQL users for the POC
-- Runs as postgres superuser during container init.

-- FCM application user (schema owner)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'fcm_user') THEN
    CREATE ROLE fcm_user WITH LOGIN PASSWORD 'fcm_password';
  END IF;
END$$;

GRANT ALL PRIVILEGES ON DATABASE fcm_poc TO fcm_user;

-- PostgreSQL 16+ requires explicit schema permissions
\c fcm_poc
GRANT ALL ON SCHEMA public TO fcm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO fcm_user;
\c postgres

-- Superset user (read-only on FCM, owner on superset metadata db)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'superset_user') THEN
    CREATE ROLE superset_user WITH LOGIN PASSWORD 'superset_password';
  END IF;
END$$;

GRANT ALL PRIVILEGES ON DATABASE superset TO superset_user;

-- PostgreSQL 16+ requires explicit schema permissions for superset metadata db
\c superset
GRANT ALL ON SCHEMA public TO superset_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO superset_user;

-- Grant FCM schema read access to Superset (applied after schema is built)
\c fcm_poc
GRANT USAGE ON SCHEMA public TO superset_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO superset_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO superset_user;
