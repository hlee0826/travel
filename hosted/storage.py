"""Only server-chosen keys in the two dedicated private buckets are accepted."""
import hashlib
import re
from urllib.parse import quote
import httpx
from hosted.config import required

BUCKETS = {'uploads': 'minhwa-uploads', 'art': 'minhwa-artwork'}


def base():
    value = required('SUPABASE_URL').rstrip('/')
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', value):
        raise RuntimeError('Use the exact Supabase project HTTPS URL.')
    return value


def path(bucket, key):
    if bucket not in BUCKETS or not re.fullmatch(r'[a-z0-9][a-z0-9/_.-]{0,240}', key) or '..' in key:
        raise ValueError('Invalid storage path.')
    return BUCKETS[bucket] + '/' + quote(key, safe='/')


def request(method, route, **kwargs):
    secret = required('SUPABASE_SERVICE_ROLE_KEY')
    with httpx.Client(timeout=60) as client:
        response = client.request(method, base() + '/storage/v1/' + route,
            headers={'Authorization': 'Bearer ' + secret, 'apikey': secret, **kwargs.pop('headers', {})}, **kwargs)
    if not response.is_success:
        raise RuntimeError('Private storage request failed.')
    return response


def read(bucket, key, limit=100 * 1024 * 1024):
    secret = required('SUPABASE_SERVICE_ROLE_KEY')
    with httpx.Client(timeout=60) as client, client.stream('GET', base() + '/storage/v1/object/authenticated/' + path(bucket, key),
            headers={'Authorization': 'Bearer ' + secret, 'apikey': secret}) as response:
        if not response.is_success:
            raise ValueError('The uploaded file is not available yet. Please retry.')
        data = bytearray()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError('The file exceeds the allowed size.')
    return bytes(data)


def put(bucket, key, raw, mime='image/png'):
    # Immutable writes: interrupted steps may repeat a write, never overwrite approved art.
    try:
        request('POST', 'object/' + path(bucket, key), content=raw, headers={'Content-Type': mime, 'x-upsert': 'false'})
    except RuntimeError:
        existing = read(bucket, key)
        if hashlib.sha256(existing).digest() != hashlib.sha256(raw).digest():
            raise RuntimeError('Immutable artwork conflict.') from None


def signed_read(bucket, key):
    value = request('POST', 'object/sign/' + path(bucket, key), json={'expiresIn': 120}).json()
    url = value.get('signedURL', '')
    if not url.startswith('/object/sign/'):
        raise RuntimeError('Invalid download link from storage.')
    return base() + '/storage/v1' + url


def signed_upload(key):
    value = request('POST', 'object/upload/sign/' + path('uploads', key), json={}).json()
    token = value.get('token')
    if not isinstance(token, str) or not token:
        raise RuntimeError('Storage did not issue upload permission.')
    return {'endpoint': base().replace('.supabase.co', '.storage.supabase.co') + '/storage/v1/upload/resumable/sign', 'token': token,
            'bucket': BUCKETS['uploads'], 'path': key}
