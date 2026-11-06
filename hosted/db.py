from contextlib import contextmanager
import os
import re
from urllib.parse import urlparse, parse_qs, unquote
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from hosted.config import required


@contextmanager
def connect():
    url = required('MINHWA_DATABASE_URL')
    if os.environ.get('VERCEL'):
        parsed = urlparse(url)
        if not re.fullmatch(r'minhwa_app(?:\.[a-z0-9]+)?', unquote(parsed.username or '')) or parse_qs(parsed.query).get('sslmode', [''])[0] not in ('require','verify-full','verify-ca'):
            raise RuntimeError('Hosted database must use the isolated Minhwa login with SSL.')
    # Transaction-pooler safe: no prepared statements or session-level locks.
    with psycopg.connect(url, prepare_threshold=None,
                         connect_timeout=10, row_factory=dict_row) as conn:
        conn.execute("SET LOCAL statement_timeout = '15s'")
        yield conn


def admission_lock(conn):
    conn.execute('SELECT pg_advisory_xact_lock(6847737206)')


def job(conn, job_id, session=None, lock=False):
    row = conn.execute('SELECT * FROM minhwa.jobs WHERE id=%s' + (' FOR UPDATE' if lock else ''), (job_id,)).fetchone()
    if not row or (session is not None and row['session_id'] != session):
        raise LookupError('Portrait not found.')
    return row


def save_job(conn, doc):
    conn.execute('UPDATE minhwa.jobs SET document=%s WHERE id=%s', (Jsonb(doc), doc['id']))
