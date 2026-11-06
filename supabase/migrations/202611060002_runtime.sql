BEGIN;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='minhwa_runtime') THEN
  CREATE ROLE minhwa_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
 END IF;
END $$;
GRANT USAGE ON SCHEMA minhwa TO minhwa_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA minhwa TO minhwa_runtime;
DO $$ DECLARE item record; BEGIN
 FOR item IN SELECT tablename FROM pg_tables WHERE schemaname='minhwa' LOOP
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='minhwa' AND tablename=item.tablename AND policyname='runtime_only') THEN
   EXECUTE format('CREATE POLICY runtime_only ON minhwa.%I TO minhwa_runtime USING (true) WITH CHECK (true)', item.tablename);
  END IF;
 END LOOP;
END $$;
COMMIT;
