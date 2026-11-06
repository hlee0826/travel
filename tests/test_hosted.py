"""Run against a disposable PostgreSQL database, never the production Supabase DB."""
import concurrent.futures
import hashlib
import io
import os
from pathlib import Path
import secrets
import subprocess
import sys
import unittest
from unittest.mock import patch
from PIL import Image
import psycopg
from psycopg.types.json import Jsonb
from fastapi.testclient import TestClient
from hosted import auth, db, service, pipeline
from app.main import app

TEST_DB = os.environ.get('MINHWA_TEST_DATABASE_URL')


class PasswordTests(unittest.TestCase):
    def test_workflow_import_does_not_load_io_pipeline(self):
        subprocess.run([sys.executable, '-c', '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'hosted.pipeline':
        raise AssertionError('Pipeline loaded during workflow replay import')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import app.workflows
'''], check=True)

    def test_password_length_and_verification(self):
        with patch.dict(os.environ, {'MINHWA_PASSWORD_HASH': auth.password_hash('TestSecret!')}):
            self.assertTrue(auth.verify_password('TestSecret!'))
            for value in ('wrong-pass!', '', 'a'*257, None):
                self.assertFalse(auth.verify_password(value))
        for value in ('short', 'a'*257, None):
            with self.assertRaises(ValueError):
                auth.password_hash(value)


@unittest.skipUnless(TEST_DB, 'Set MINHWA_TEST_DATABASE_URL to a disposable database.')
class HostedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not TEST_DB.startswith('postgresql://stevenlee@127.0.0.1:55487/'):
            raise RuntimeError('Tests are restricted to the disposable loopback database.')
        cls.env = patch.dict(os.environ, {'MINHWA_DATABASE_URL':TEST_DB,'MINHWA_PUBLIC_ORIGIN':'https://studio.test',
            'SUPABASE_URL':'https://project.supabase.co','MINHWA_SESSION_SECRET':'s'*40,
            'MINHWA_PASSWORD_HASH':auth.password_hash('test-password-for-studio-only'),
            'MINHWA_GENERATION_ENABLED':'true','MINHWA_DAILY_BUDGET_CENTS':'30000',
            'MINHWA_DISPATCH_SECRET':'d'*40,'VERCEL_ENV':'production'})
        cls.env.start()
        with psycopg.connect(TEST_DB, autocommit=True) as conn:
            for file in sorted(Path('supabase/migrations').glob('*.sql')):
                conn.execute(file.read_text())

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()

    def setUp(self):
        with db.connect() as conn:
            conn.execute('TRUNCATE minhwa.sessions,minhwa.login_limits,minhwa.uploads,minhwa.jobs,minhwa.attempts,minhwa.steps,minhwa.orders CASCADE')
        self.client=TestClient(app, base_url='https://studio.test', raise_server_exceptions=False)
        self.headers={'Origin':'https://studio.test'}
        self.token=auth.login('test-password-for-studio-only','test')
        self.session=auth.session(self.token)
        self.client.cookies.set(auth.COOKIE,self.token)

    def demo(self):
        return service.create_job(self.session, {'key':secrets.token_hex(12),'demo':True,'style':'peony','name':'Miso'})

    def real(self):
        key=secrets.token_hex(12)
        output=io.BytesIO(); Image.new('RGB',(600,800),'red').save(output,'PNG'); raw=output.getvalue()
        with db.connect() as conn:
            tickets={}
            for role in ('face','body'):
                ticket=hashlib.sha256((self.session+key+':'+role).encode()).hexdigest()[:24]
                tickets[role]=ticket
                conn.execute("INSERT INTO minhwa.uploads(id,session_id,object_key,bytes,mime,expires) VALUES(%s,%s,%s,%s,'image/png',now()+interval '1 hour')",(ticket,self.session,ticket+'/original',len(raw)))
        body={'key':key,'face_upload_id':tickets['face'],'body_upload_id':tickets['body'],'style':'peony','name':'Miso','rights':True,'generation_consent':True}
        with patch('hosted.storage.read',return_value=raw),patch('hosted.storage.put'):
            doc=service.create_job(self.session,body)
        return doc,body

    def test_password_origin_assets_and_body_gate(self):
        self.client.cookies.clear()
        for path in ['/','/assets/peony-cat.png','/.env.local','/app/main.py','/media/'+'a'*24+'/source.png']:
            self.assertEqual(self.client.get(path,follow_redirects=False).status_code,303)
        self.assertEqual(self.client.get('/api/session').status_code,401)
        self.assertEqual(self.client.get('/login').headers['Referrer-Policy'],'same-origin')
        self.assertEqual(self.client.post('/login',data={'password':'test-password-for-studio-only'}).status_code,403)
        response=self.client.post('/login',data={'password':'test-password-for-studio-only'},headers=self.headers,follow_redirects=False)
        self.assertEqual(response.status_code,303)
        self.assertIn('Secure',response.headers['set-cookie']);self.assertIn('HttpOnly',response.headers['set-cookie'])
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/.env.local').status_code,404)
        self.assertEqual(self.client.post('/api/jobs',json={'demo':True},headers={'Origin':'https://evil.test'}).status_code,403)
        self.assertEqual(self.client.post('/api/jobs',content='x'*65537,headers={**self.headers,'Content-Type':'application/json'}).status_code,400)
        self.assertEqual(self.client.post('/api/internal/dispatch',json={}).status_code,404)

    def test_session_ownership_and_logout(self):
        doc=self.demo()
        self.assertEqual(self.client.get('/api/jobs/'+doc['id']).status_code,200)
        other=auth.login('test-password-for-studio-only','other')
        self.client.cookies.set(auth.COOKIE,other)
        self.assertEqual(self.client.get('/api/jobs/'+doc['id']).status_code,404)
        with patch('hosted.storage.signed_read') as sign:
            self.assertEqual(self.client.get('/media/'+doc['id']+'/source.png').status_code,404)
            sign.assert_not_called()
        self.client.post('/api/logout',json={},headers=self.headers)
        self.assertIsNone(auth.session(other))
        self.assertEqual(self.client.get('/api/session').status_code,401)

    def test_idempotent_submission_and_retry(self):
        doc,body=self.real()
        with patch('hosted.storage.read') as read:
            self.assertEqual(service.create_job(self.session,body)['id'],doc['id']);read.assert_not_called()
        with self.assertRaises(ValueError):
            service.create_job(self.session,{**body,'name':'Other'})
        busy_retry={'key':secrets.token_hex(12)}
        doc=service.retry(self.session,doc['id'],busy_retry)
        with db.connect() as conn:
            doc['status']='failed';db.save_job(conn,doc)
        service.retry(self.session,doc['id'],busy_retry)
        with db.connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) n FROM minhwa.attempts').fetchone()['n'],1)
        retry={'key':secrets.token_hex(12),'feedback':''}
        again=service.retry(self.session,doc['id'],retry)
        with db.connect() as conn:
            again['status']='failed';db.save_job(conn,again)
        service.retry(self.session,doc['id'],retry)
        with db.connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) n FROM minhwa.attempts').fetchone()['n'],2)

    def test_atomic_daily_cap_under_concurrent_admission(self):
        docs=[self.demo() for _ in range(4)]
        def reserve(doc):
            doc.update(demo=False,completed_batches=0,source_hash=doc['id'])
            try:
                with db.connect() as conn:
                    db.admission_lock(conn);service.reserve(conn,doc)
                return True
            except ValueError:
                return False
        with patch.dict(os.environ,{'MINHWA_DAILY_BUDGET_CENTS':'600'}), concurrent.futures.ThreadPoolExecutor(4) as pool:
            self.assertEqual(sum(pool.map(reserve,docs)),2)

    def test_paid_stage_is_never_repeated(self):
        doc,_=self.real(); attempt=doc['attempt_id']
        photo={'verdict':{'usable':True,'pet_count':1,'species':'dog','same_pet':True,'face_visible':True,'body_visible':True,'details_clear':True,'markings_clear':True,'identity':'white dog','unseen_features':'none','reason':'good'}}
        with patch('hosted.pipeline.perform',return_value=photo) as perform:
            self.assertEqual(pipeline.run_stage(doc['id'],attempt,'checking_photo'),'continue')
            self.assertEqual(pipeline.run_stage(doc['id'],attempt,'checking_photo'),'continue')
            self.assertEqual(perform.call_count,1)
        with patch('hosted.pipeline.perform',side_effect=TimeoutError('secret provider details')) as perform:
            self.assertEqual(pipeline.run_stage(doc['id'],attempt,'painting'),'stopped')
            self.assertEqual(pipeline.run_stage(doc['id'],attempt,'painting'),'stopped')
            self.assertEqual(perform.call_count,1)
        result=self.client.get('/api/jobs/'+doc['id']).json()
        self.assertEqual(result['status'],'uncertain');self.assertNotIn('secret',str(result));self.assertFalse(result['can_retry'])

    def test_inflight_and_stale_claims_do_not_reissue(self):
        doc,_=self.real(); attempt=doc['attempt_id']
        with db.connect() as conn:
            conn.execute("INSERT INTO minhwa.steps(attempt_id,name,status,claim) VALUES(%s,'checking_photo','running','original')",(attempt,))
        with patch('hosted.pipeline.perform') as perform:
            self.assertEqual(pipeline.run_stage(doc['id'],attempt,'checking_photo'),'busy')
            with db.connect() as conn:
                conn.execute("UPDATE minhwa.steps SET started=now()-interval '20 minutes'")
            self.assertEqual(pipeline.run_stage(doc['id'],attempt,'checking_photo'),'stopped')
            perform.assert_not_called()

    def test_quality_gate_and_artifacts_publish_atomically(self):
        doc,_=self.real(); attempt=doc['attempt_id']
        responses=[{'verdict':{'usable':True,'pet_count':1,'species':'cat','same_pet':True,'face_visible':True,'body_visible':True,'details_clear':True,'markings_clear':True}},
                   {'reference_hashes':['a']*6}, {'verdict':{k:True for k in pipeline.ART_FIELDS}},
                   {'candidate':{'id':attempt,'url':f'/media/{doc["id"]}/art-{attempt}.png','review_status':'approved','artifacts_version':1,'dimensions':[2432,3040]}}]
        with patch('hosted.pipeline.perform',side_effect=responses):
            for stage in pipeline.STAGES:
                pipeline.run_stage(doc['id'],attempt,stage)
        result=self.client.get('/api/jobs/'+doc['id']).json()
        self.assertEqual(result['status'],'ready');self.assertEqual(len(result['candidates']),1)
        self.assertEqual(pipeline.run_stage(doc['id'],attempt,'rendering'),'ready')
        with db.connect() as conn:
            self.assertEqual(db.job(conn,doc['id'])['document']['completed_batches'],1)

    def test_flagged_art_stays_private(self):
        doc,_=self.real(); attempt=doc['attempt_id']
        results=[{'verdict':{'usable':True,'pet_count':1,'species':'cat','same_pet':True,'face_visible':True,'body_visible':True,'details_clear':True,'markings_clear':True}},
                 {},{'verdict':{'likeness':False}}]
        with patch('hosted.pipeline.perform',side_effect=results):
            for stage in pipeline.STAGES[:3]:pipeline.run_stage(doc['id'],attempt,stage)
        result=self.client.get('/api/jobs/'+doc['id']).json()
        self.assertEqual(result['status'],'awaiting_review');self.assertEqual(result['candidates'],[])
        self.assertEqual(self.client.get(f'/media/{doc["id"]}/art-{attempt}.png').status_code,404)
        with self.assertRaises(ValueError):service.order(self.session,{'key':secrets.token_hex(12),'job_id':doc['id'],'candidate_id':attempt,'approved':True,'product':'digital','size':'digital'})

    def test_actual_pipeline_keeps_six_references_and_immutable_downloads(self):
        doc,_=self.real(); attempt=doc['attempt_id']
        source=io.BytesIO();Image.new('RGB',(600,800),'red').save(source,'PNG')
        art=io.BytesIO();Image.new('RGB',pipeline.IMAGE_SIZE,'green').save(art,'PNG')
        objects={('art',doc['id']+'/face.png'):source.getvalue(), ('art',doc['id']+'/body.png'):source.getvalue()}
        def put(bucket,key,raw,mime='image/png'):
            if (bucket,key) in objects:self.assertEqual(objects[bucket,key],raw)
            objects[bucket,key]=raw
        photo={'usable':True,'pet_count':1,'species':'dog','same_pet':True,'face_visible':True,'body_visible':True,'details_clear':True,'markings_clear':True,'identity':'white dog','unseen_features':'none','reason':'good'}
        quality={k:True for k in pipeline.ART_FIELDS};quality['reason']='passed'
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only'}),patch('hosted.storage.read',side_effect=lambda b,k,**kw:objects[b,k]),patch('hosted.storage.put',side_effect=put),patch('hosted.pipeline.OpenAIReview') as reviewer,patch('hosted.pipeline.OpenAIImages') as images:
            reviewer.return_value.photo.return_value=(photo,{})
            reviewer.return_value.artwork.return_value=(quality,{})
            images.return_value.generate.return_value=(art.getvalue(),{})
            for stage in pipeline.STAGES:pipeline.run_stage(doc['id'],attempt,stage)
            inputs=images.return_value.generate.call_args.args[0]
            self.assertEqual(len(inputs['referenced_image_paths']),6)
            self.assertEqual(len(inputs['reference_hashes']),6)
            self.assertIn('FACE IDENTITY',inputs['prompt'])
            self.assertEqual(len(reviewer.return_value.artwork.call_args.args[2]),4)
        self.assertIn(('art',f'{doc["id"]}/{attempt}/master.png'),objects)
        self.assertIn(('art',f'{doc["id"]}/{attempt}/print-12x16.png'),objects)
        body={'key':secrets.token_hex(12),'job_id':doc['id'],'candidate_id':attempt,'approved':True,'product':'digital','size':'digital'}
        order=service.order(self.session,body)
        self.assertEqual(service.order(self.session,body)['id'],order['id'])
        with patch('hosted.storage.signed_read',return_value='https://project.supabase.co/test-signed') as sign:
            response=self.client.get(f'/api/orders/{order["id"]}/download/png')
            self.assertEqual(response.status_code,200)
            self.assertEqual(sign.call_args.args,('art',f'{doc["id"]}/{attempt}/master.png'))
            self.client.cookies.set(auth.COOKIE,auth.login('test-password-for-studio-only','other'))
            sign.reset_mock()
            self.assertEqual(self.client.get(f'/api/orders/{order["id"]}/download/png').status_code,404)
            sign.assert_not_called()

    def test_storage_policy_blocks_minhwa_without_changing_other_buckets(self):
        with db.connect() as conn:
            for role in ('anon','authenticated'):
                if not conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
                    conn.execute('CREATE ROLE '+role+' NOLOGIN')
            conn.execute('CREATE SCHEMA IF NOT EXISTS storage')
            conn.execute('CREATE TABLE IF NOT EXISTS storage.objects(id int,bucket_id text)')
            conn.execute('ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY')
            conn.execute('GRANT USAGE ON SCHEMA storage TO anon, authenticated')
            conn.execute('GRANT SELECT, INSERT ON storage.objects TO anon, authenticated')
            conn.execute('DROP POLICY IF EXISTS broad_existing ON storage.objects')
            conn.execute('CREATE POLICY broad_existing ON storage.objects TO anon,authenticated USING(true) WITH CHECK(true)')
            conn.execute('TRUNCATE storage.objects')
            conn.execute("INSERT INTO storage.objects VALUES(1,'minhwa-uploads'),(2,'minhwa-artwork'),(3,'existing-pinned-bucket')")
            conn.execute(Path('supabase/migrations/202611060003_private_storage.sql').read_text())
            conn.execute('SET LOCAL ROLE anon')
            rows=conn.execute('SELECT id FROM storage.objects').fetchall()
            self.assertEqual(rows,[{'id':3}])
            conn.execute("INSERT INTO storage.objects VALUES(4,'existing-pinned-bucket')")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("INSERT INTO storage.objects VALUES(5,'minhwa-uploads')")

    def test_hosted_connection_refuses_admin_credentials(self):
        with patch.dict(os.environ,{'VERCEL':'1','MINHWA_DATABASE_URL':TEST_DB}),patch('hosted.db.psycopg.connect') as connect:
            with self.assertRaises(RuntimeError):
                with db.connect():pass
            connect.assert_not_called()

    def test_upload_ticket_reuses_completed_upload_and_limits_size(self):
        body={'key':secrets.token_hex(12),'role':'face','bytes':4,'mime':'image/png'}
        with patch('hosted.storage.signed_upload',return_value={'token':'scoped-upload-test-token'}) as sign,patch('hosted.storage.read',return_value=b'data') as read:
            ticket=service.upload_ticket(self.session,body)
            self.assertEqual(ticket['token'],'scoped-upload-test-token');read.assert_not_called()
            again=service.upload_ticket(self.session,body)
            self.assertEqual(again,{'id':ticket['id'],'complete':True});self.assertEqual(sign.call_count,1)
        with self.assertRaises(ValueError):service.upload_ticket(self.session,{**body,'bytes':21*1024*1024})
        with self.assertRaises(ValueError):service.upload_ticket(self.session,{**body,'mime':'text/html'})
        with patch('hosted.storage.request') as request:
            request.return_value.json.return_value={'token':'scoped-upload-test-token'}
            signed=service.storage.signed_upload('a'*24+'/original')
            self.assertEqual(signed['endpoint'],'https://project.storage.supabase.co/storage/v1/upload/resumable/sign')
            self.assertEqual(signed['token'],'scoped-upload-test-token')

    def test_runtime_role_is_scoped_and_rls_enabled(self):
        with db.connect() as conn:
            rows=conn.execute("SELECT relrowsecurity FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace WHERE n.nspname='minhwa' AND relkind='r'").fetchall()
            self.assertTrue(all(r['relrowsecurity'] for r in rows))
            conn.execute('SET LOCAL ROLE minhwa_runtime')
            self.assertTrue(conn.execute('SELECT id FROM minhwa.sessions').fetchone())
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute('CREATE TABLE public.minhwa_must_not_exist(id int)')

if __name__=='__main__':unittest.main()
