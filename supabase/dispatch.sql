-- Run after creating Vault secrets minhwa_origin and minhwa_dispatch_secret.
-- pg_net sends after transaction commit; cron recovers interrupted dispatches.
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE OR REPLACE FUNCTION minhwa.wake_dispatch() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE target text; token text;
BEGIN
 IF NOT EXISTS (SELECT 1 FROM minhwa.attempts WHERE status IN ('queued','running')
   AND (dispatch_at IS NULL OR dispatch_at<now()-interval '15 minutes')) THEN RETURN; END IF;
 SELECT decrypted_secret INTO target FROM vault.decrypted_secrets WHERE name='minhwa_origin';
 SELECT decrypted_secret INTO token FROM vault.decrypted_secrets WHERE name='minhwa_dispatch_secret';
 IF target IS NULL OR token IS NULL THEN RAISE EXCEPTION 'Minhwa dispatch is not configured'; END IF;
 PERFORM net.http_post(url:=target||'/api/internal/dispatch',
   headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||token),
   body:='{}'::jsonb,timeout_milliseconds:=10000);
END $$;
REVOKE ALL ON FUNCTION minhwa.wake_dispatch() FROM PUBLIC;
CREATE OR REPLACE FUNCTION minhwa.attempt_inserted() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN PERFORM minhwa.wake_dispatch(); RETURN NEW; END $$;
REVOKE ALL ON FUNCTION minhwa.attempt_inserted() FROM PUBLIC;
DROP TRIGGER IF EXISTS minhwa_dispatch ON minhwa.attempts;
CREATE TRIGGER minhwa_dispatch AFTER INSERT ON minhwa.attempts FOR EACH STATEMENT EXECUTE FUNCTION minhwa.attempt_inserted();
SELECT cron.schedule('minhwa-dispatch-recovery','* * * * *','SELECT minhwa.wake_dispatch()');
