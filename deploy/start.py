"""One private studio worker and an authenticated proxy, behind Render's TLS edge."""
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def validate(env):
    origin = env.get('MINHWA_PUBLIC_ORIGIN', '')
    if not re.fullmatch(r'https://[a-z0-9]+(?:[.-][a-z0-9]+)*', origin):
        raise ValueError('Set MINHWA_PUBLIC_ORIGIN to the exact HTTPS origin, without a trailing slash.')
    if not re.fullmatch(r'\$2[aby]\$1[0-6]\$[./A-Za-z0-9]{53}', env.get('MINHWA_PASSWORD_HASH', '')):
        raise ValueError('Set MINHWA_PASSWORD_HASH to a bcrypt hash (cost 10–16), never a plain password.')
    if not env.get('OPENAI_API_KEY') or env.get('MINHWA_IMAGE_PROVIDER') != 'openai':
        raise ValueError('Configure the server-side OpenAI key and provider before hosting.')
    if not Path(env.get('MINHWA_DATA_DIR', '')).is_absolute():
        raise ValueError('Set MINHWA_DATA_DIR to a directory on the persistent disk.')
    port = env.get('PORT', '10000')
    if not port.isdigit() or not 1024 <= int(port) <= 65535 or int(port) == 4187:
        raise ValueError('Choose a public proxy port between 1024 and 65535, other than 4187.')
    return origin.removeprefix('https://')


def main():
    try:
        host = validate(os.environ)
    except ValueError as exc:
        sys.exit(str(exc))
    os.umask(0o077)
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    children = []
    try:
        children.append(subprocess.Popen([sys.executable, 'server.py'], cwd=ROOT))
        # The proxy has no reason to receive the OpenAI credential.
        proxy_env = {k: os.environ[k] for k in ('PATH', 'HOME', 'PORT', 'MINHWA_PASSWORD_HASH') if k in os.environ}
        proxy_env['MINHWA_PUBLIC_HOST'] = host
        children.append(subprocess.Popen(['caddy', 'run', '--config', 'deploy/Caddyfile', '--adapter', 'caddyfile'], cwd=ROOT, env=proxy_env))
        while not stopping and all(child.poll() is None for child in children):
            time.sleep(.5)
        return 0 if stopping else 1
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    sys.exit(main())
