import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def required(name):
    value = os.environ.get(name, '')
    if not value:
        raise RuntimeError(f'Missing server setting: {name}')
    return value


def origin():
    value = required('MINHWA_PUBLIC_ORIGIN')
    local = os.environ.get('MINHWA_LOCAL_HOSTED_TEST') == '1' and not os.environ.get('VERCEL')
    if not re.fullmatch(r'https://[a-z0-9]+(?:[.-][a-z0-9]+)*', value):
        if not (local and re.fullmatch(r'http://127\.0\.0\.1:\d+', value)):
            raise RuntimeError('Set an exact HTTPS studio origin.')
    return value


def generation_enabled():
    return os.environ.get('MINHWA_GENERATION_ENABLED') == 'true' and os.environ.get('VERCEL_ENV', 'development') != 'preview'
