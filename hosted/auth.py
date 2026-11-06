import hashlib
import hmac
import secrets
import re
from datetime import datetime, timezone, timedelta
from hosted import db
from hosted.config import required

COOKIE = '__Host-minhwa'


def password_hash(password, salt=None):
    if not isinstance(password, str) or not 8 <= len(password) <= 256:
        raise ValueError('Use a unique password of 8–256 characters.')
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'scrypt${salt}${digest}'


def verify_password(password):
    encoded = required('MINHWA_PASSWORD_HASH')
    if not re.fullmatch(r'scrypt\$[a-f0-9]{32}\$[a-f0-9]{128}', encoded):
        raise RuntimeError('Invalid password hash configuration.')
    if not isinstance(password, str) or not 8 <= len(password) <= 256:
        return False
    return hmac.compare_digest(password_hash(password, encoded.split('$')[1]), encoded)


def digest(value):
    secret = required('MINHWA_SESSION_SECRET')
    if len(secret) < 32:
        raise RuntimeError('Session secret must be at least 32 characters.')
    # Rotating either secret invalidates all existing browser sessions.
    return hmac.new(secret.encode(), (required('MINHWA_PASSWORD_HASH') + value).encode(), hashlib.sha256).hexdigest()


def rate_limit(key, maximum, seconds):
    with db.connect() as conn:
        row = conn.execute('''INSERT INTO minhwa.login_limits(key,hits,resets) VALUES(%s,1,now()+%s * interval '1 second')
          ON CONFLICT(key) DO UPDATE SET hits=CASE WHEN minhwa.login_limits.resets <= now() THEN 1 ELSE minhwa.login_limits.hits+1 END,
          resets=CASE WHEN minhwa.login_limits.resets <= now() THEN excluded.resets ELSE minhwa.login_limits.resets END
          RETURNING hits''', (key, seconds)).fetchone()
    return row['hits'] <= maximum


def login(password, client):
    global_ok = rate_limit('login:global', 100, 900)
    client_ok = rate_limit('login:' + digest(client), 10, 900)
    if not global_ok or not client_ok:
        raise PermissionError('Too many login attempts. Please try again in 15 minutes.')
    if not verify_password(password):
        return None
    token, session = secrets.token_urlsafe(32), secrets.token_hex(12)
    with db.connect() as conn:
        conn.execute('INSERT INTO minhwa.sessions(id,token_hash,expires) VALUES(%s,%s,%s)',
                     (session, digest(token), datetime.now(timezone.utc) + timedelta(days=7)))
    return token


def session(token):
    if not token or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        return None
    with db.connect() as conn:
        row = conn.execute('SELECT id FROM minhwa.sessions WHERE token_hash=%s AND expires > now()', (digest(token),)).fetchone()
    return row['id'] if row else None


def logout(token):
    if token:
        with db.connect() as conn:
            conn.execute('UPDATE minhwa.sessions SET expires=now() WHERE token_hash=%s', (digest(token),))
