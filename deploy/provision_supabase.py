"""Apply only Minhwa schema/buckets. Run with the existing project's admin DB URL."""
import os
from pathlib import Path
import secrets
import sys
import psycopg
from psycopg import sql
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from hosted import storage
from hosted.config import required


def provision():
    root=Path(__file__).resolve().parent.parent
    password=required('MINHWA_DATABASE_PASSWORD')
    if len(password)<32:
        raise ValueError('Use a database password of at least 32 characters.')
    with psycopg.connect(required('MINHWA_ADMIN_DATABASE_URL'),prepare_threshold=None) as conn:
        for file in sorted((root/'supabase/migrations').glob('*.sql')):
            conn.execute(file.read_text())
        exists=conn.execute("SELECT 1 FROM pg_roles WHERE rolname='minhwa_app'").fetchone()
        if not exists:
            conn.execute(sql.SQL('CREATE ROLE minhwa_app LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT').format(sql.Literal(password)))
        else:
            raise ValueError('Minhwa database login already exists; refusing to replace its password.')
        conn.execute('GRANT minhwa_runtime TO minhwa_app')
        conn.execute('ALTER ROLE minhwa_app SET statement_timeout = 15000')
    existing={r['id']:r for r in storage.request('GET','bucket').json()}
    for name,limit in [('minhwa-uploads',20*1024*1024),('minhwa-artwork',50*1024*1024)]:
        if name in existing:
            if existing[name]['public']:
                raise ValueError('Existing Minhwa bucket is public; investigate before proceeding.')
            continue
        mime=['image/png','image/jpeg','image/webp','image/heic','image/heif'] if name.endswith('uploads') else ['image/png','image/jpeg']
        storage.request('POST','bucket',json={'id':name,'name':name,'public':False,'file_size_limit':limit,'allowed_mime_types':mime})
    print('Isolated Minhwa schema, runtime login, and private buckets provisioned.')

if __name__=='__main__':
    try:provision()
    except Exception:
        raise SystemExit('Provisioning stopped. Inspect configuration privately; credentials were not printed.') from None
