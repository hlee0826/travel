"""Create a private hosted environment file without echoing credentials."""
import getpass
import os
from pathlib import Path
import secrets
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from hosted.auth import password_hash


def main():
    target=Path(__file__).resolve().parent.parent/'.env.hosted.local'
    if target.exists():
        raise SystemExit('Hosted configuration already exists; edit it privately to rotate settings.')
    password=getpass.getpass('Choose a unique studio password (at least 8 characters): ')
    encoded=password_hash(password)
    if password!=getpass.getpass('Confirm studio password: '):
        raise SystemExit('Passwords did not match; no file was written.')
    values={
        'MINHWA_PUBLIC_ORIGIN':'https://minhwa.pinnedby.com',
        'MINHWA_PASSWORD_HASH':encoded,
        'MINHWA_SESSION_SECRET':secrets.token_urlsafe(48),
        'MINHWA_DISPATCH_SECRET':secrets.token_urlsafe(48),
        'MINHWA_DATABASE_URL':getpass.getpass('Minhwa-only PostgreSQL pooler URL: '),
        'SUPABASE_URL':getpass.getpass('Existing Supabase project URL: '),
        'SUPABASE_SERVICE_ROLE_KEY':getpass.getpass('Server-only Supabase service-role key: '),
        'OPENAI_API_KEY':getpass.getpass('OpenAI image + Responses API key: '),
        'MINHWA_GENERATION_ENABLED':'false',
        'MINHWA_DAILY_BUDGET_CENTS':'30000',
        'MINHWA_API_TIMEOUT_SECONDS':'240',
    }
    if any(not v or '\n' in v or '\r' in v for v in values.values()):
        raise SystemExit('Invalid or empty setting; nothing was written.')
    with os.fdopen(os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        f.write(''.join(k+'='+v+'\n' for k,v in values.items()))
    assert target.stat().st_mode & 0o777 == 0o600
    print('Private configuration saved. Live generation stays disabled until deployment checks pass.')

if __name__=='__main__':main()
