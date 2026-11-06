-- Isolated application schema. Never expose this schema through the Supabase Data API.
BEGIN;
CREATE SCHEMA IF NOT EXISTS minhwa;
REVOKE ALL ON SCHEMA minhwa FROM PUBLIC;
CREATE TABLE IF NOT EXISTS minhwa.sessions (
 id text PRIMARY KEY, token_hash text UNIQUE NOT NULL,
 expires timestamptz NOT NULL, created timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS minhwa.login_limits (
 key text PRIMARY KEY, hits integer NOT NULL, resets timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS minhwa.uploads (
 id text PRIMARY KEY, session_id text NOT NULL REFERENCES minhwa.sessions(id),
 created timestamptz NOT NULL DEFAULT now(), expires timestamptz NOT NULL,
 object_key text UNIQUE NOT NULL, bytes integer NOT NULL CHECK(bytes > 0 AND bytes <= 20971520),
 mime text NOT NULL
);
CREATE TABLE IF NOT EXISTS minhwa.jobs (
 id text PRIMARY KEY, session_id text NOT NULL REFERENCES minhwa.sessions(id),
 submit_key text NOT NULL, source_hash text, document jsonb NOT NULL,
 created timestamptz NOT NULL DEFAULT now(), UNIQUE(session_id, submit_key)
);
CREATE TABLE IF NOT EXISTS minhwa.attempts (
 id text PRIMARY KEY, job_id text NOT NULL REFERENCES minhwa.jobs(id),
 created timestamptz NOT NULL DEFAULT now(), reserved_cents integer NOT NULL CHECK(reserved_cents >= 0),
 run_id text, dispatch_at timestamptz, status text NOT NULL DEFAULT 'queued',
 reconciliation text
);
CREATE INDEX IF NOT EXISTS attempts_created ON minhwa.attempts(created);
CREATE TABLE IF NOT EXISTS minhwa.steps (
 attempt_id text NOT NULL REFERENCES minhwa.attempts(id), name text NOT NULL,
 status text NOT NULL CHECK(status IN ('running','completed','uncertain')),
 claim text NOT NULL, started timestamptz NOT NULL DEFAULT now(), result jsonb,
 PRIMARY KEY(attempt_id, name)
);
CREATE TABLE IF NOT EXISTS minhwa.orders (
 id text PRIMARY KEY, session_id text NOT NULL REFERENCES minhwa.sessions(id),
 job_id text NOT NULL REFERENCES minhwa.jobs(id), document jsonb NOT NULL,
 created timestamptz NOT NULL DEFAULT now()
);
-- RLS is defense in depth; the application uses a private schema and a server-only role.
ALTER TABLE minhwa.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE minhwa.login_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE minhwa.uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE minhwa.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE minhwa.attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE minhwa.steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE minhwa.orders ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA minhwa FROM PUBLIC;
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
  REVOKE ALL ON SCHEMA minhwa FROM anon, authenticated;
  REVOKE ALL ON ALL TABLES IN SCHEMA minhwa FROM anon, authenticated;
 END IF;
END $$;
COMMIT;
