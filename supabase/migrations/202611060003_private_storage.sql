-- Restrict only Minhwa buckets, even if the shared project has permissive policies.
DO $$ BEGIN
 IF to_regclass('storage.objects') IS NOT NULL
 AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon')
 AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated')
 AND NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='storage' AND tablename='objects' AND policyname='minhwa_private_objects') THEN
  CREATE POLICY minhwa_private_objects ON storage.objects AS RESTRICTIVE
   FOR ALL TO anon, authenticated
   USING (bucket_id NOT IN ('minhwa-uploads','minhwa-artwork'))
   WITH CHECK (bucket_id NOT IN ('minhwa-uploads','minhwa-artwork'));
 END IF;
END $$;
