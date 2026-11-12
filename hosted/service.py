import hashlib
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from psycopg.types.json import Jsonb
from hosted import db, storage, auth
from hosted.config import ROOT, generation_enabled
from server import ID, STYLES, FEEDBACK, quote, image_bytes
from minhwa_workflow.workflow import WORKFLOW_VERSION


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError('Invalid portrait reference.')
    return value


def options(body):
    style, name = body.get('style'), body.get('name', '')
    if not isinstance(style,str) or style not in STYLES or not isinstance(name, str) or len(name.strip()) > 24 or any(ord(c) < 32 for c in name):
        raise ValueError('Choose a garden and a pet name of at most 24 characters.')
    product = body.get('product', 'digital')
    size = 'digital' if product == 'digital' else body.get('size', '5x7')
    if not isinstance(product,str) or not isinstance(size,str):
        raise ValueError('Choose an available keepsake and size.')
    quote(product, size)
    return {'style': style, 'name': name.strip(), 'product_preference': product, 'size_preference': size}


def upload_ticket(session, body):
    if not generation_enabled():
        raise ValueError('Live generation is not enabled in this environment.')
    key = identifier(body.get('key'))
    size, mime = body.get('bytes'), body.get('mime')
    if type(size) is not int or not 0 < size <= 20*1024*1024 or mime not in ('image/png','image/jpeg','image/webp','image/heic','image/heif'):
        raise ValueError('Choose a JPEG, PNG, WebP, or HEIC photo under 20 MB.')
    if not auth.rate_limit('upload:' + session, 30, 3600) or not auth.rate_limit('upload:global', 200, 86400):
        raise ValueError('The studio upload allowance has been reached. Please try later.')
    ticket_id = hashlib.sha256((session + key).encode()).hexdigest()[:24]
    with db.connect() as conn:
        row = conn.execute('''INSERT INTO minhwa.uploads(id,session_id,object_key,bytes,mime,expires)
            VALUES(%s,%s,%s,%s,%s,now()+interval '2 hours') ON CONFLICT(id) DO NOTHING RETURNING *''',
            (ticket_id,session,ticket_id+'/original',size,mime)).fetchone()
        created = row is not None
        if not row:
            row = conn.execute('SELECT * FROM minhwa.uploads WHERE id=%s', (ticket_id,)).fetchone()
            if row['session_id'] != session or row['bytes'] != size or row['mime'] != mime or row['expires'] < datetime.now(timezone.utc):
                raise ValueError('Please select your photo again to renew the upload.')
    if not created:
        try:
            if len(storage.read('uploads', row['object_key'], limit=20*1024*1024)) == size:
                return {'id':ticket_id, 'complete':True}
        except ValueError:
            pass
    return {'id': ticket_id, **storage.signed_upload(row['object_key'])}


def reserve(conn, doc):
    # Caller holds the global admission lock: budget, attempt count, and status change commit together.
    rows = conn.execute('SELECT * FROM minhwa.attempts WHERE job_id=%s', (doc['id'],)).fetchall()
    if len(rows) >= 3 or doc['completed_batches'] >= 2:
        raise ValueError('The portrait attempt allowance has been used.')
    totals = conn.execute('''SELECT coalesce(sum(a.reserved_cents),0) AS budget,
        count(*) FILTER(WHERE j.session_id=%s) AS session_count,
        count(*) FILTER(WHERE j.source_hash=%s) AS photo_count
        FROM minhwa.attempts a JOIN minhwa.jobs j ON j.id=a.job_id WHERE a.created > now()-interval '24 hours' ''',
        (doc['session'], doc['source_hash'])).fetchone()
    if totals['budget'] + 600 > int(os.environ.get('MINHWA_DAILY_BUDGET_CENTS', '30000')):
        raise ValueError('The studio has reached its testing allowance. No painting was started.')
    exempt = conn.execute('SELECT 1 FROM minhwa.login_limits WHERE key=%s AND resets>now()',
                          ('allowance:' + doc['session'],)).fetchone()
    if not exempt and (totals['session_count'] >= 6 or totals['photo_count'] >= 3):
        raise ValueError('The daily allowance for this session or photo has been reached.')
    attempt_id = secrets.token_hex(12)
    conn.execute('INSERT INTO minhwa.attempts(id,job_id,reserved_cents) VALUES(%s,%s,600)', (attempt_id,doc['id']))
    doc.update(status='queued', error=None, attempt_id=attempt_id, updated=time.time())
    db.save_job(conn, doc)
    return doc


def create_job(session, body):
    selected = options(body)
    demo = body.get('demo') is True
    key = identifier(body.get('key'))
    with db.connect() as conn:
        existing = conn.execute('SELECT document FROM minhwa.jobs WHERE session_id=%s AND submit_key=%s', (session,key)).fetchone()
    if existing:
        doc = existing['document']
        if any(doc[k] != v for k,v in selected.items()) or doc['demo'] != demo or (not demo and doc['id'] != body.get('upload_id')):
            raise ValueError('That submission reference belongs to another selection. Please select your photo again.')
        return doc
    if not demo and (not generation_enabled() or body.get('rights') is not True or body.get('generation_consent') is not True):
        raise ValueError('Confirm you may use this photo and send it to OpenAI for generation.')
    job_id, source_hash, dimensions = secrets.token_hex(12), None, None
    if not demo:
        job_id = identifier(body.get('upload_id'))
        if job_id != hashlib.sha256((session + key).encode()).hexdigest()[:24]:
            raise ValueError('Upload reference does not match this submission.')
        with db.connect() as conn:
            ticket = conn.execute('SELECT * FROM minhwa.uploads WHERE id=%s AND session_id=%s AND expires>now()', (job_id,session)).fetchone()
        if not ticket:
            raise ValueError('Upload permission expired. Please select your photo again.')
        uploaded = storage.read('uploads', ticket['object_key'], limit=20*1024*1024)
        if len(uploaded) != ticket['bytes']:
            raise ValueError('The upload is incomplete. Please try again.')
        raw, dimensions = image_bytes(uploaded)
        if min(dimensions) < 600:
            raise ValueError('Please choose a clearer photo, at least 600 pixels wide and tall.')
        source_hash = hashlib.sha256(raw).hexdigest()
        storage.put('art', job_id + '/source.png', raw)
    doc = {'id':job_id, 'session':session, **selected, 'demo':demo, 'created':time.time(),
           'status':'ready' if demo else 'queued', 'source_hash':source_hash,
           'source_dimensions':dimensions, 'source':None if demo else f'/media/{job_id}/source.png',
           'completed_batches':1 if demo else 0, 'candidates':[], 'error':None,
           'workflow_version':WORKFLOW_VERSION, 'generation_provider':'openai',
           'consent_at':None if demo else time.time()}
    if demo:
        asset = STYLES[doc['style']][1]
        with Image.open(ROOT/'hosted_web/assets'/asset) as im:
            doc['candidates'] = [{'id':'sample', 'url':'/assets/'+asset, 'dimensions':list(im.size)}]
    with db.connect() as conn:
        db.admission_lock(conn)
        existing = conn.execute('SELECT document FROM minhwa.jobs WHERE session_id=%s AND submit_key=%s', (session,key)).fetchone()
        if existing:
            doc = existing['document']
            if any(doc[k] != v for k,v in selected.items()) or doc['demo'] != demo:
                raise ValueError('Submission already used for another selection.')
            return doc
        count = conn.execute('SELECT count(*) n FROM minhwa.jobs WHERE session_id=%s', (session,)).fetchone()['n']
        if count >= 50:
            raise ValueError('This session has reached its portrait limit.')
        conn.execute('INSERT INTO minhwa.jobs(id,session_id,submit_key,source_hash,document) VALUES(%s,%s,%s,%s,%s)',
                     (job_id,session,key,source_hash,Jsonb(doc)))
        if not demo:
            reserve(conn, doc)
    return doc


def retry(session, job_id, body):
    if not generation_enabled():
        raise ValueError('Live generation is not enabled.')
    retry_key = identifier(body.get('key'))
    feedback = body.get('feedback', '')
    if not isinstance(feedback,str) or (feedback and feedback not in FEEDBACK):
        raise ValueError('Choose an available correction.')
    with db.connect() as conn:
        db.admission_lock(conn)
        doc = db.job(conn, identifier(job_id), session, lock=True)['document']
        if retry_key in doc.get('retry_keys', []):
            return doc
        if len(doc.get('retry_keys', [])) >= 64:
            raise ValueError('Too many retry requests for this portrait. Please refresh Your pieces.')
        if doc['status'] in ('queued','checking_photo','painting_identity','checking_identity',
                             'awaiting_identity_approval','painting_integrated','checking_artwork',
                             'rendering','awaiting_review'):
            doc.setdefault('retry_keys', []).append(retry_key)
            db.save_job(conn, doc)
            return doc
        if doc['demo'] or doc['status'] not in ('ready','rejected','failed'):
            raise ValueError('This portrait needs a studio check or a new photo before retrying.')
        doc.setdefault('retry_keys', []).append(retry_key)
        doc['feedback'] = feedback
        return reserve(conn, doc)


def approve_identity(session, job_id, body):
    key = identifier(body.get('key'))
    if type(body.get('approved')) is not bool:
        raise ValueError('Choose whether this identity study looks like your pet.')
    with db.connect() as conn:
        doc = db.job(conn, identifier(job_id), session, lock=True)['document']
        if key in doc.get('identity_approval_keys', []):
            return doc
        if doc.get('identity_study_status') != 'pending' or doc['status'] != 'awaiting_identity_approval':
            raise ValueError('This identity study is not waiting for approval.')
        doc.setdefault('identity_approval_keys', []).append(key)
        if body['approved']:
            doc.update(identity_study_status='approved', identity_approved_at=time.time(),
                       status='queued', error=None)
            conn.execute("UPDATE minhwa.attempts SET status='queued',dispatch_at=NULL WHERE id=%s", (doc['attempt_id'],))
        else:
            doc.update(identity_study_status='rejected', status='rejected',
                       error='This identity study was not approved. Request another interpretation.')
            conn.execute("UPDATE minhwa.attempts SET status='rejected' WHERE id=%s", (doc['attempt_id'],))
        db.save_job(conn, doc)
        return doc


def public_job(doc, conn):
    keys = ('id','name','style','demo','created','status','source','source_dimensions','completed_batches','error','product_preference','size_preference','identity_study','identity_study_status')
    result = {k:doc.get(k) for k in keys}
    result['candidates'] = [{k:c[k] for k in ('id','url','dimensions','artifacts_version') if k in c}
                            for c in doc['candidates'] if c.get('review_status','approved') == 'approved']
    attempts = conn.execute('SELECT count(*) n FROM minhwa.attempts WHERE job_id=%s', (doc['id'],)).fetchone()['n']
    result['can_retry'] = not doc['demo'] and doc['status'] in ('ready','failed','rejected') and doc['completed_batches'] < 2 and attempts < 3
    result['request'] = None
    return result


def order(session, body):
    key = identifier(body.get('key'))
    if not isinstance(body.get('product'),str) or not isinstance(body.get('size'),str):
        raise ValueError('Choose an available keepsake and size.')
    totals = quote(body.get('product'), body.get('size'))
    with db.connect() as conn:
        db.admission_lock(conn)
        doc = db.job(conn, identifier(body.get('job_id')), session)['document']
        candidate = next((c for c in doc['candidates'] if c['id']==body.get('candidate_id') and c.get('review_status','approved')=='approved'),None)
        if not candidate or body.get('approved') is not True:
            raise ValueError('Approve an available painting before placing your test order.')
        existing = conn.execute('SELECT * FROM minhwa.orders WHERE id=%s', (key,)).fetchone()
        if existing:
            previous = existing['document']
            if existing['session_id'] != session or (previous['job_id'],previous['candidate']['id'],previous['product'],previous['size']) != (doc['id'],candidate['id'],body['product'],body['size']):
                raise ValueError('Checkout reference already used.')
            return previous
        clean_candidate = {k:candidate[k] for k in ('id','url','dimensions','artifacts_version','master_sha256') if k in candidate}
        result = {'id':key,'number':'MH-'+key[:6].upper(),'job_id':doc['id'],'name':doc['name'],'style':doc['style'],
                  'demo':doc['demo'],'candidate':clean_candidate,'product':body['product'],'size':body['size'],
                  'totals':totals,'created':time.time(),'test':True,
                  'status':'digital_ready' if body['product']=='digital' else 'awaiting_review'}
        conn.execute('INSERT INTO minhwa.orders(id,session_id,job_id,document) VALUES(%s,%s,%s,%s)', (key,session,doc['id'],Jsonb(result)))
        return result
