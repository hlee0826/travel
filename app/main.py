"""All customer routes, including assets, pass through the password gate."""
import asyncio
import hmac
import json
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from hosted import auth, db, service, storage
from artifacts import matted_print
from hosted.config import ROOT, origin, required, generation_enabled
from hosted.dispatch import dispatch

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
WEB = ROOT/'hosted_web'


async def body(request):
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 65536:
            raise ValueError('Request is too large. Upload photos using the photo picker.')
    return bytes(data)


def login_page(message=''):
    # Native form submission works without JavaScript or publicly served application assets.
    return HTMLResponse('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Minhwa · Private studio</title><style>body{background:#f4eee2;color:#323c31;font:18px Georgia,serif;max-width:420px;margin:15vh auto;padding:24px}h1{font-weight:400;font-size:42px}label{display:block}input,button{box-sizing:border-box;width:100%;padding:16px;margin-top:14px;font:inherit}button{background:#344a3f;color:white;border:0;cursor:pointer}p{line-height:1.6}</style>
    <main><p>MINHWA · PRIVATE PREVIEW</p><h1>A little world,<br>just for you.</h1><form action="/login" method="post"><label for="password">Studio password</label><input id="password" name="password" type="password" autocomplete="current-password" required maxlength="256"><button>Enter the studio</button></form><p role="alert">''' + message + '</p></main></html>')


@app.middleware('http')
async def protect(request: Request, call_next):
    try:
        expected = origin()
        if request.headers.get('host') != urlparse(expected).netloc:
            response = JSONResponse({'error':'Unknown studio address.'}, status_code=403)
        elif request.method not in ('GET','HEAD','POST'):
            response = JSONResponse({'error':'Method not allowed.'}, status_code=405)
        elif request.url.path == '/api/internal/dispatch':
            secret = required('MINHWA_DISPATCH_SECRET')
            if request.method != 'POST' or len(secret)<32 or not hmac.compare_digest(request.headers.get('authorization',''), 'Bearer '+secret):
                response = JSONResponse({'error':'Not found.'}, status_code=404)
            else:
                await body(request)
                response = JSONResponse({'dispatched':await dispatch()})
        elif request.method == 'POST' and request.headers.get('origin') != expected:
            response = JSONResponse({'error':'Please submit from the studio website.'}, status_code=403)
        elif request.url.path == '/login':
            if request.method == 'POST':
                if request.headers.get('content-type','').split(';')[0] != 'application/x-www-form-urlencoded':
                    raise ValueError('Invalid sign-in request.')
                data = parse_qs((await body(request)).decode())
                token = await asyncio.to_thread(auth.login, data.get('password',[''])[0], request.headers.get('x-real-ip', request.client.host if request.client else 'unknown'))
                if token:
                    response = RedirectResponse('/', status_code=303)
                    response.set_cookie(auth.COOKIE, token, max_age=7*86400, secure=True, httponly=True, samesite='strict', path='/')
                else:
                    response = login_page('That password did not match. Please try again.')
                    response.status_code = 401
            else:
                response = login_page()
        else:
            session = await asyncio.to_thread(auth.session, request.cookies.get(auth.COOKIE))
            if not session:
                response = JSONResponse({'error':'Please sign in to the studio again.'}, status_code=401) if request.url.path.startswith('/api/') else RedirectResponse('/login', status_code=303)
            else:
                request.state.session = session
                if request.method == 'POST':
                    if request.headers.get('content-type','').split(';')[0] != 'application/json':
                        raise ValueError('Send a JSON request.')
                    try:
                        data = json.loads(await body(request))
                    except (ValueError, UnicodeError):
                        raise ValueError('Invalid request.') from None
                    if not isinstance(data, dict):
                        raise ValueError('Invalid request.')
                    request.state.data = data
                response = await call_next(request)
    except PermissionError:
        response = JSONResponse({'error':'Too many attempts. Please try again in 15 minutes.'}, status_code=429)
    except ValueError as exc:
        response = JSONResponse({'error':str(exc)}, status_code=400)
    except Exception:
        response = JSONResponse({'error':'The studio is temporarily unavailable. Your saved work is safe.'}, status_code=503)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    try:
        supabase = storage.base()
    except RuntimeError:
        supabase = ''
    response.headers['Content-Security-Policy'] = f"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data: {supabase}; connect-src 'self' {supabase} {supabase.replace('.supabase.co', '.storage.supabase.co')}; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"
    return response


@app.exception_handler(ValueError)
async def invalid(request, exc):
    return JSONResponse({'error':str(exc)}, status_code=400)


@app.exception_handler(LookupError)
async def missing(request, exc):
    return JSONResponse({'error':'This piece is not available in your session.'}, status_code=404)


@app.get('/api/session')
def session(request: Request):
    with db.connect() as conn:
        jobs = conn.execute('SELECT document FROM minhwa.jobs WHERE session_id=%s ORDER BY created DESC', (request.state.session,)).fetchall()
        orders = conn.execute('SELECT document FROM minhwa.orders WHERE session_id=%s ORDER BY created DESC', (request.state.session,)).fetchall()
        return {'hosted':True, 'generation_provider':'openai' if generation_enabled() else 'disabled',
                'jobs':[service.public_job(r['document'], conn) for r in jobs], 'orders':[r['document'] for r in orders]}


@app.post('/api/logout')
def logout(request: Request):
    auth.logout(request.cookies.get(auth.COOKIE))
    response = JSONResponse({'ok':True})
    response.delete_cookie(auth.COOKIE, secure=True, httponly=True, samesite='strict')
    return response


@app.post('/api/uploads')
def upload(request: Request):
    return service.upload_ticket(request.state.session, request.state.data)


@app.post('/api/jobs')
async def create(request: Request):
    doc = await asyncio.to_thread(service.create_job, request.state.session, request.state.data)
    if not doc['demo']:
        await dispatch()
    with db.connect() as conn:
        return service.public_job(doc, conn)


@app.get('/api/jobs/{job_id}')
def get_job(job_id: str, request: Request):
    with db.connect() as conn:
        return service.public_job(db.job(conn, service.identifier(job_id), request.state.session)['document'], conn)


@app.post('/api/jobs/{job_id}/retry')
async def retry(job_id: str, request: Request):
    doc = await asyncio.to_thread(service.retry, request.state.session, job_id, request.state.data)
    await dispatch()
    with db.connect() as conn:
        return service.public_job(doc, conn)


@app.post('/api/jobs/{job_id}/identity-approval')
async def identity_approval(job_id: str, request: Request):
    doc = await asyncio.to_thread(service.approve_identity, request.state.session, job_id, request.state.data)
    if doc['status'] == 'queued':
        await dispatch()
    with db.connect() as conn:
        return service.public_job(doc, conn)


@app.post('/api/orders')
def order(request: Request):
    return service.order(request.state.session, request.state.data)


@app.post('/api/orders/{order_id}/advance')
def advance(order_id: str, request: Request):
    with db.connect() as conn:
        row = conn.execute('SELECT document FROM minhwa.orders WHERE id=%s AND session_id=%s FOR UPDATE', (service.identifier(order_id),request.state.session)).fetchone()
        if not row:
            raise LookupError()
        doc = row['document']
        statuses = ('awaiting_review','in_production','shipped','delivered')
        if doc['status'] not in statuses or doc['status']=='delivered':
            raise ValueError('This test order cannot advance further.')
        doc['status'] = statuses[statuses.index(doc['status'])+1]
        from psycopg.types.json import Jsonb
        conn.execute('UPDATE minhwa.orders SET document=%s WHERE id=%s', (Jsonb(doc),order_id))
    return doc


@app.get('/api/orders/{order_id}/download/{kind}')
def download(order_id: str, kind: str, request: Request):
    names = {'png':'master.png','jpeg':'master.jpg','print':'print-12x16.png'}
    if kind not in names:
        raise LookupError()
    with db.connect() as conn:
        row = conn.execute('SELECT document FROM minhwa.orders WHERE id=%s AND session_id=%s', (service.identifier(order_id),request.state.session)).fetchone()
    if not row:
        raise LookupError()
    doc = row['document']
    if not doc['candidate'].get('artifacts_version') or (kind=='print' and doc['size'] not in ('5x7','12x16')):
        raise LookupError()
    if kind == 'print' and doc['size'] == '5x7':
        names['print'] = 'print-5x7.png'
        prefix = f'{doc["job_id"]}/{doc["candidate"]["id"]}/'
        storage.put('art', prefix + names['print'], matted_print(storage.read('art', prefix + 'master.png'), '5x7'))
    return {'url':storage.signed_read('art', f'{doc["job_id"]}/{doc["candidate"]["id"]}/{names[kind]}')}


@app.get('/media/{job_id}/{filename}')
def media(job_id: str, filename: str, request: Request):
    with db.connect() as conn:
        doc = db.job(conn, service.identifier(job_id), request.state.session)['document']
    if filename == 'source.png' and not doc['demo']:
        key = job_id+'/source.png'
    elif filename == 'identity-study.png' and doc.get('identity_study_status') in ('pending','approved'):
        key = job_id+'/identity-study.png'
    else:
        candidate = next((c for c in doc['candidates'] if c.get('review_status')=='approved' and filename==f'art-{c["id"]}.png'),None)
        if not candidate:
            raise LookupError()
        key = f'{job_id}/{candidate["id"]}/preview.png'
    return RedirectResponse(storage.signed_read('art', key), status_code=307)


@app.get('/{path:path}')
def website(path: str):
    target = (WEB/(path or 'index.html')).resolve()
    if not target.is_relative_to(WEB.resolve()) or not target.is_file() or any(part.startswith('.') for part in Path(path).parts):
        raise LookupError()
    return FileResponse(target)
