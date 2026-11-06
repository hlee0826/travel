"""Minhwa studio; hosted testing runs behind the authenticated deployment proxy."""
import base64
import binascii
import io
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import threading
import time
import hashlib
import fcntl
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from minhwa_workflow import workflow
from generation import OpenAIImages, OpenAIReview, settings, ART_FIELDS, IMAGE_SIZE
from artifacts import artwork_files, matted_print

register_heif_opener(thumbnails=False)

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('MINHWA_DATA_DIR', ROOT / '.studio')).resolve()
PUBLIC = ROOT / 'hosted_web'
GENERATOR = None
REVIEWER = None
WAKE = threading.Event()
STOP = threading.Event()
DAILY_BUDGET_CENTS = 1500
PUBLIC_ORIGIN = ''
ATTEMPT_RESERVATION_CENTS = 300
ACTIVE = {'queued', 'checking_photo', 'painting', 'checking_artwork'}
FEEDBACK = {'likeness': 'Preserve the distinctive ears, muzzle and recognizable face more closely.',
            'markings': 'Match the visible coat colors and patch locations more closely.',
            'painting': 'Use clearly painted pigment shapes, not photographic fur or a cutout.',
            'interaction': 'Align the head, muzzle and pupils with one nearby butterfly.',
            'composition': 'Keep calm open space and safe margins around the face, ears and paws.'}


class StorageLock:
    """One shared lock for the HTTP process and local review commands."""
    def __init__(self):
        self.thread = threading.RLock()
        self.depth = 0

    def __enter__(self):
        self.thread.acquire()
        try:
            if not self.depth:
                DATA.mkdir(parents=True, exist_ok=True)
                self.file = (DATA / '.storage.lock').open('a')
                fcntl.flock(self.file, fcntl.LOCK_EX)
            self.depth += 1
        except Exception:
            self.thread.release()
            raise
        return self

    def __exit__(self, *args):
        self.depth -= 1
        if not self.depth:
            fcntl.flock(self.file, fcntl.LOCK_UN)
            self.file.close()
        self.thread.release()


LOCK = StorageLock()
Image.MAX_IMAGE_PIXELS = 40_000_000
STYLES = {'peony': ('Peonies and butterflies', 'peony-cat.png'), 'lotus': ('Lotus garden', 'lotus-dog.png')}
PRICES = {'digital': {'digital': 1900}, 'print': {'8x10': 3900, '12x16': 5900, '16x20': 6900}, 'framed': {'8x10': 7900, '12x16': 10900, '16x20': 12900}}
ID = re.compile(r'^[a-f0-9]{24}$')


def read_json(path):
    return json.loads(path.read_text())


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(0o600)
    temporary.replace(path)


def save_bytes(path, raw):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(0o600)
    temporary.replace(path)


def image_bytes(raw):
    if len(raw) > 20 * 1024 * 1024:
        raise ValueError('Please choose an image smaller than 20 MB.')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in ('JPEG', 'PNG', 'WEBP', 'HEIF'):
                raise ValueError('Use a JPEG, PNG, WebP, or HEIC image.')
            if im.width * im.height > 40_000_000 or min(im.size) < 100:
                raise ValueError('Choose an image at least 100 pixels wide and tall, and under 40 megapixels.')
            im.load()
            clean = ImageOps.exif_transpose(im).convert('RGB')
            dimensions = clean.size
            out = io.BytesIO()
            clean.save(out, 'PNG')
            return out.getvalue(), dimensions
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('This image could not be read. Please try a different photo.') from exc


def quote(product, size):
    if product not in PRICES or size not in PRICES[product]:
        raise ValueError('Choose an available product and size.')
    subtotal = PRICES[product][size]
    shipping = 0 if product == 'digital' else 600
    return {'subtotal': subtotal, 'shipping': shipping, 'tax': 0, 'total': subtotal + shipping, 'currency': 'USD'}


def job_path(job_id):
    if not ID.fullmatch(job_id):
        raise ValueError('Invalid portrait ID.')
    return DATA / 'jobs' / job_id


def prepare_generation(job):
    inputs = workflow.generation_inputs(job_path(job['id']) / 'source.png', job['style'])
    folder = job_path(job['id'])
    job['workflow_version'] = workflow.WORKFLOW_VERSION
    job['style_anchors'] = [p.name for p in workflow.STYLE_ANCHORS]
    save_json(folder / 'generation-inputs.json', inputs)
    (folder / 'request.txt').write_text(f'''Generate the pending Minhwa portrait {job['id']} in this local workspace. Art direction: {workflow.WORKFLOW_VERSION}.
Read {folder / 'generation-inputs.json'} and inspect every image listed in referenced_image_paths.
Call the built-in image generation tool using that JSON's prompt, referenced_image_paths, and transparent_background arguments. Attach all five actual image files in the listed order. Do not substitute text descriptions, omit anchors, use previous outputs, apply local filters, or call an external model API.
Generate one or two candidates. Before attaching, inspect each against the identity photo and style anchors for likeness, traditional painting style, coherent anatomy, a fresh composition, and an unambiguous head-and-eye sightline to the butterfly. Revise failures.
Save the outputs in this workspace, then run:
.venv/bin/python studio.py complete {job['id']} /absolute/path/candidate-1.png [/absolute/path/candidate-2.png]
The website will detect the completed artwork. Do not replace the source photo or style anchors.
''')


def public_job(job):
    request = None if job['demo'] or job.get('generation_provider') == 'openai' else (job_path(job['id']) / 'request.txt').read_text()
    visible = {k: v for k, v in job.items() if k not in ('session', 'attempts', 'submit_key', 'source_hash', 'identity')}
    visible['candidates'] = [{k: v for k, v in c.items() if k not in ('usage', 'request_id', 'reference_hashes', 'quality_report')}
        for c in job['candidates'] if c.get('review_status', 'approved') == 'approved']
    visible['can_retry'] = (job['status'] in ('ready', 'rejected', 'failed') and job['completed_batches'] < 2
                            and len(job.get('attempts', [])) < 3)
    return visible | {'request': request}


def complete_artwork(job_id, images, metadata=None):
    with LOCK:
        folder = job_path(job_id)
        job = read_json(folder / 'job.json')
        if job['demo'] or job['status'] != 'awaiting_artwork':
            raise ValueError('Only a pending real-photo job can receive artwork.')
        if not 1 <= len(images) <= 2:
            raise ValueError('Attach one or two portrait candidates.')
        prepared = [image_bytes(raw) for raw in images]
        for raw, dimensions in prepared:
            candidate_id = secrets.token_hex(8)
            filename = f'art-{candidate_id}.png'
            save_bytes(folder / filename, raw)
            job['candidates'].append({'id': candidate_id, 'url': f'/media/{job_id}/{filename}',
                'dimensions': list(dimensions), 'workflow_version': job.get('workflow_version', 'minhwa-reference-v1'),
                'style_anchors': job.get('style_anchors', []), **(metadata or {})})
        job['completed_batches'] += 1
        job['status'], job['error'] = 'ready', None
        save_json(folder / 'job.json', job)
        return job


def all_jobs():
    return [read_json(p) for p in (DATA / 'jobs').glob('*/job.json')]


def start_generation(job):
    if not GENERATOR:
        return
    if not REVIEWER:
        raise ValueError('Photo and artwork checks are not configured. Please contact the studio.')
    if job['status'] in ACTIVE and job.get('attempts'):
        return
    jobs = all_jobs()
    recent = [(j, a) for j in jobs for a in j.get('attempts', []) if a['created'] > time.time() - 86400]
    if sum(a['reserved_cents'] for _, a in recent) + ATTEMPT_RESERVATION_CENTS > DAILY_BUDGET_CENTS:
        raise ValueError('The studio has reached its local testing allowance. No new painting was started. Please try again later.')
    if len(job.get('attempts', [])) >= 3:
        raise ValueError('This portrait has reached its attempt limit. Please contact the studio.')
    if sum(j['session'] == job['session'] for j, _ in recent) >= 6:
        raise ValueError('Your daily portrait allowance has been reached. Please try tomorrow.')
    if sum(j.get('source_hash') == job.get('source_hash') for j, _ in recent) >= 3:
        raise ValueError('This photo has reached its daily attempt limit. Please try tomorrow.')
    attempt = {'id': secrets.token_hex(8), 'created': time.time(), 'status': 'queued',
               'reserved_cents': ATTEMPT_RESERVATION_CENTS, 'calls': {}}
    job.setdefault('attempts', []).append(attempt)
    job.update(status='queued', generation_provider='openai', error=None)
    save_json(job_path(job['id']) / 'job.json', job)
    WAKE.set()


def update_job(job, **changes):
    job.update(changes)
    job['updated'] = time.time()
    save_json(job_path(job['id']) / 'job.json', job)


def provider_call(job, stage, fn):
    # Persist intent BEFORE sending; an interrupted call requires reconciliation.
    with LOCK:
        attempt = job['attempts'][-1]
        attempt['status'] = stage
        attempt['calls'][stage] = {'status': 'in_flight', 'started': time.time()}
        update_job(job, status=stage)
    value, metadata = fn()
    with LOCK:
        attempt['calls'][stage].update(status='completed', finished=time.time(), **metadata)
        update_job(job)
    return value, metadata


def generate_artwork(job_id, generator, reviewer=None):
    reviewer = reviewer or REVIEWER
    with LOCK:
        job = read_json(job_path(job_id) / 'job.json')
    folder = job_path(job_id)
    attempt = job['attempts'][-1]
    workspace = folder / 'attempts' / attempt['id']
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        photo, photo_meta = provider_call(job, 'checking_photo', lambda: reviewer.photo(folder / 'source.png', job['session']))
        save_json(workspace / 'photo-review.json', {'verdict': photo, **photo_meta})
        if not (photo['usable'] and photo['pet_count'] == 1 and photo['species'].lower() in ('cat', 'dog')
                and photo['face_visible'] and photo['details_clear']):
            with LOCK:
                attempt['status'] = 'needs_photo'
                update_job(job, status='needs_photo', error=photo['reason'] or 'Please choose a clear photo of one cat or dog.')
            return
        identity = photo['identity'] + '\nUnseen or uncertain: ' + photo['unseen_features']
        inputs = workflow.generation_inputs(folder / 'source.png', job['style'], identity, FEEDBACK.get(job.get('feedback'), ''))
        save_json(workspace / 'inputs.json', inputs)
        raw, metadata = provider_call(job, 'painting', lambda: generator.generate(inputs, job['session']))
        raw, dimensions = image_bytes(raw)
        if dimensions != IMAGE_SIZE:
            raise ValueError('The returned artwork has an unexpected size. The studio will check this attempt.')
        if hashlib.sha256(raw).hexdigest() == job['source_hash']:
            raise ValueError('The returned artwork repeats the source photo. It cannot be accepted.')
        artwork = workspace / 'artwork.png'
        save_bytes(artwork, raw)
        save_json(workspace / 'generation.json', metadata)
        quality, review_meta = provider_call(job, 'checking_artwork', lambda: reviewer.artwork(
            folder / 'source.png', artwork, inputs['referenced_image_paths'][1:], job['style'], identity, job['session']))
        save_json(workspace / 'artwork-review.json', {'verdict': quality, **review_meta})
        with LOCK:
            candidate_id = attempt['id']
            filename = f'art-{candidate_id}.png'
            save_bytes(folder / filename, raw)
            job['candidates'].append({'id': candidate_id, 'url': f'/media/{job_id}/{filename}',
                'dimensions': list(dimensions), 'workflow_version': workflow.WORKFLOW_VERSION,
                'style_anchors': [p.name for p in workflow.STYLE_ANCHORS],
                'reference_hashes': inputs['reference_hashes'], 'review_status': 'pending',
                'quality_report': quality, **metadata})
            attempt['status'] = 'awaiting_review'
            update_job(job, status='awaiting_review', identity=identity, error=None)
            if all(quality.get(k) is True for k in ART_FIELDS if k != 'reason'):
                review_candidate(job_id, candidate_id, True,
                    'All nine automated artwork checks passed. Customer likeness approval is still required.',
                    reviewer='automated')
    except Exception as exc:
        with LOCK:
            # A failure may have incurred cost. Preserve the reservation and all old art.
            attempt['status'] = 'uncertain'
            update_job(job, status='uncertain', error=str(exc) if isinstance(exc, ValueError)
                       else 'The studio could not finish this attempt. It needs review before another is started.')


def review_candidate(job_id, candidate_id, approve, note, override=False, reviewer='operator'):
    if not note.strip():
        raise ValueError('Record the visual review findings.')
    with LOCK:
        job = read_json(job_path(job_id) / 'job.json')
        candidate = next((c for c in job['candidates'] if c['id'] == candidate_id), None)
        if not candidate or candidate.get('review_status') != 'pending' or job['status'] != 'awaiting_review':
            raise ValueError('Only a pending candidate can receive a studio review.')
        passed = all(candidate['quality_report'].get(k) is True for k in ART_FIELDS if k != 'reason')
        if approve and not passed and not override:
            raise ValueError('Automated checks flagged issues. Reject or explicitly override with a visual review explanation.')
        if approve:
            folder = job_path(job_id)
            rendered = folder / 'artifacts' / candidate_id
            rendered.mkdir(parents=True, exist_ok=True)
            files = artwork_files((folder / f'art-{candidate_id}.png').read_bytes(), job['name'])
            for filename, raw in files.items():
                save_bytes(rendered / filename, raw)
            save_bytes(rendered / 'print-12x16.png', matted_print(files['master.png']))
            candidate.update(artifacts_version=1, master_sha256=hashlib.sha256(files['master.png']).hexdigest())
        candidate.update(review_status='approved' if approve else 'rejected',
                         studio_review={'reviewer': reviewer, 'note': note.strip()[:2000], 'at': time.time(), 'override': bool(override)})
        if approve:
            job['completed_batches'] += 1
        job['attempts'][-1]['status'] = 'approved' if approve else 'rejected'
        update_job(job, status='ready' if approve else 'rejected',
                   error=None if approve else 'This painting did not meet our artwork checks. You can request another attempt.')
        return job


def reconcile_attempt(job_id, note):
    if not note.strip():
        raise ValueError('Record what was checked in provider usage before allowing a retry.')
    with LOCK:
        job = read_json(job_path(job_id) / 'job.json')
        if job['status'] != 'uncertain':
            raise ValueError('Only an uncertain attempt can be reconciled.')
        job['attempts'][-1]['reconciliation'] = {'note': note.strip()[:2000], 'at': time.time()}
        job['attempts'][-1]['status'] = 'failed'
        update_job(job, status='failed', error='The studio checked the interrupted attempt. You can now try again.')
        return job


def recover_jobs():
    with LOCK:
        for job in all_jobs():
            if job.get('generation_provider') == 'openai' and job['status'] in (ACTIVE - {'queued'}) | {'awaiting_artwork'}:
                if job.get('attempts'):
                    job['attempts'][-1]['status'] = 'uncertain'
                update_job(job, status='uncertain', error='The studio restarted while checking or painting. We will review this attempt before starting another.')


def worker_loop():
    while not STOP.is_set():
        with LOCK:
            queued = sorted((j for j in all_jobs() if j['status'] == 'queued'), key=lambda j: j['attempts'][-1]['created'])
        if queued:
            generate_artwork(queued[0]['id'], GENERATOR, REVIEWER)
        else:
            WAKE.wait(1)
            WAKE.clear()


class Handler(BaseHTTPRequestHandler):
    server_version = 'MinhwaLocal/1.0'

    def log_message(self, fmt, *args):
        pass

    def send(self, status, data, content_type='application/json', cookie=None):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode()
        elif isinstance(data, str):
            data = data.encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Robots-Tag', 'noindex, nofollow, noarchive')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob: data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if cookie:
            secure = '; Secure' if PUBLIC_ORIGIN else ''
            self.send_header('Set-Cookie', f'minhwa_session={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000{secure}')
        self.end_headers()
        self.wfile.write(data)

    def valid_request(self):
        host = self.headers.get('Host', '')
        allowed = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
        if host not in allowed:
            self.send(403, {'error': 'This studio is available only on this computer.'})
            return False
        origin = self.headers.get('Origin')
        origins = {PUBLIC_ORIGIN} if PUBLIC_ORIGIN else {f'http://{h}' for h in allowed}
        if origin and origin not in origins:
            self.send(403, {'error': 'Cross-site requests are not allowed.'})
            return False
        return True

    def session(self, create=False):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            value = cookies['minhwa_session'].value if 'minhwa_session' in cookies else ''
        except Exception:
            value = ''
        if ID.fullmatch(value) and (DATA / 'sessions' / f'{value}.json').exists():
            return value, False
        if create:
            value = secrets.token_hex(12)
            save_json(DATA / 'sessions' / f'{value}.json', {'created': time.time()})
            return value, True
        raise PermissionError('Open the studio first to begin a local session.')

    def owned_job(self, job_id, session):
        path = job_path(job_id) / 'job.json'
        if not path.exists():
            raise FileNotFoundError()
        job = read_json(path)
        if job['session'] != session:
            raise FileNotFoundError()
        return job

    def do_GET(self):
        if not self.valid_request():
            return
        try:
            path = urlparse(self.path).path
            with LOCK:
                if path == '/api/session':
                    session, new = self.session(create=True)
                    jobs = [public_job(j) for p in (DATA / 'jobs').glob('*/job.json') if (j := read_json(p))['session'] == session]
                    orders = [o for p in (DATA / 'orders').glob('*.json') if (o := read_json(p))['session'] == session]
                    for order in orders:
                        order.pop('session', None)
                    return self.send(200, {'jobs': sorted(jobs, key=lambda j: j['created'], reverse=True), 'orders': sorted(orders, key=lambda o: o['created'], reverse=True), 'generation_provider': 'openai' if GENERATOR else 'manual'}, cookie=session if new else None)
                match = re.fullmatch(r'/api/jobs/([a-f0-9]{24})', path)
                if match:
                    session, _ = self.session()
                    return self.send(200, public_job(self.owned_job(match[1], session)))
                match = re.fullmatch(r'/media/([a-f0-9]{24})/(source\.png|art-[a-f0-9]+\.png)', path)
                if match:
                    session, _ = self.session()
                    job = self.owned_job(match[1], session)
                    if match[2] != 'source.png' and not any(c['url'].endswith('/' + match[2]) and c.get('review_status', 'approved') == 'approved' for c in job['candidates']):
                        raise FileNotFoundError()
                    candidate = next((c for c in job['candidates'] if c['url'].endswith('/' + match[2])), None)
                    if candidate and candidate.get('artifacts_version'):
                        return self.send(200, (job_path(match[1]) / 'artifacts' / candidate['id'] / 'preview.png').read_bytes(), 'image/png')
                    return self.send(200, (job_path(match[1]) / match[2]).read_bytes(), 'image/png')
                match = re.fullmatch(r'/api/orders/([a-f0-9]{24})/download/(png|jpeg|print)', path)
                if match:
                    session, _ = self.session()
                    order = read_json(DATA / 'orders' / (match[1] + '.json'))
                    if order['session'] != session or not order['candidate'].get('artifacts_version'):
                        raise FileNotFoundError()
                    if match[2] == 'print' and order['size'] != '12x16':
                        raise FileNotFoundError()
                    filename = {'png': 'master.png', 'jpeg': 'master.jpg', 'print': 'print-12x16.png'}[match[2]]
                    file = job_path(order['job_id']) / 'artifacts' / order['candidate']['id'] / filename
                    return self.send(200, file.read_bytes(), 'image/jpeg' if match[2] == 'jpeg' else 'image/png')
            # Only the public directory is served; source code and uploaded photos are never static routes.
            target = (PUBLIC / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
            if not target.is_relative_to(PUBLIC) or not target.is_file():
                raise FileNotFoundError()
            self.send(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
        except (FileNotFoundError, PermissionError):
            self.send(404, {'error': 'This item was not found in your local session.'})
        except (ValueError, OSError):
            self.send(400, {'error': 'Could not read this item.'})

    def do_POST(self):
        if not self.valid_request():
            return
        try:
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Use a JSON request.')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 29 * 1024 * 1024:
                return self.send(413, {'error': 'This upload is too large.'})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Invalid request.')
            path = urlparse(self.path).path
            with LOCK:
                session, _ = self.session()
                if path == '/api/jobs':
                    if body.get('style') not in STYLES:
                        raise ValueError('Choose one of the available art styles.')
                    name = body.get('name', '')
                    if not isinstance(name, str) or len(name.strip()) > 24 or any(ord(c) < 32 for c in name):
                        raise ValueError('Use a pet name of 24 characters or fewer.')
                    demo = body.get('demo') is True
                    preference = body.get('product', 'digital')
                    preferred_size = 'digital' if preference == 'digital' else body.get('size', '8x10')
                    quote(preference, preferred_size)
                    submit_key = body.get('key')
                    if not demo and GENERATOR and (not isinstance(submit_key, str) or not ID.fullmatch(submit_key)):
                        raise ValueError('The upload reference is missing. Please select your photo again.')
                    raw, dimensions = None, None
                    if not demo:
                        if body.get('rights') is not True:
                            raise ValueError('Confirm you may use this photo.')
                        if GENERATOR and body.get('generation_consent') is not True:
                            raise ValueError('Confirm this photo may be sent to OpenAI to create your portrait.')
                        encoded = body.get('image', '')
                        if not isinstance(encoded, str):
                            raise ValueError('Choose a pet photo.')
                        try:
                            raw, dimensions = image_bytes(base64.b64decode(encoded, validate=True))
                        except (binascii.Error, TypeError) as exc:
                            raise ValueError('The upload was not a valid image.') from exc
                        if min(dimensions) < 600:
                            raise ValueError('Please choose a clearer photo, at least 600 pixels wide and tall.')
                    source_hash = hashlib.sha256(raw).hexdigest() if raw else None
                    if submit_key:
                        existing = next((j for j in all_jobs() if j['session'] == session and j.get('submit_key') == submit_key), None)
                        if existing:
                            if (existing.get('source_hash'), existing['name'], existing['style']) != (source_hash, name.strip(), body['style']):
                                raise ValueError('This upload reference was used for another photo or selection. Please select your photo again.')
                            return self.send(200, public_job(existing))
                    if len([j for j in all_jobs() if j['session'] == session]) >= 50:
                        raise ValueError('This session has reached its project limit. Please contact the studio.')
                    job_id = secrets.token_hex(12)
                    folder = job_path(job_id)
                    folder.mkdir(parents=True)
                    job = {'id': job_id, 'session': session, 'name': name.strip(), 'style': body['style'], 'demo': demo, 'status': 'ready' if demo else 'awaiting_artwork', 'created': time.time(), 'completed_batches': 1 if demo else 0, 'candidates': [], 'source': None, 'source_dimensions': dimensions, 'error': None, 'workflow_version': workflow.WORKFLOW_VERSION}
                    job.update(submit_key=submit_key, source_hash=source_hash, consent_at=time.time() if not demo else None,
                               product_preference=preference, size_preference=preferred_size)
                    if demo:
                        asset = STYLES[job['style']][1]
                        if not (PUBLIC / 'assets' / asset).exists():
                            raise ValueError('The sample artwork is still being prepared. Try again shortly.')
                        with Image.open(PUBLIC / 'assets' / asset) as im:
                            size = list(im.size)
                        job['candidates'] = [{'id': 'sample', 'url': f'/assets/{asset}', 'dimensions': size}]
                    else:
                        save_bytes(folder / 'source.png', raw)
                        job['source'] = f'/media/{job_id}/source.png'
                        prepare_generation(job)
                    if not demo:
                        start_generation(job)
                    save_json(folder / 'job.json', job)
                    return self.send(201, public_job(job))
                match = re.fullmatch(r'/api/jobs/([a-f0-9]{24})/retry', path)
                if match:
                    job = self.owned_job(match[1], session)
                    if job['demo'] or job['completed_batches'] >= 2:
                        raise ValueError('The included portrait batches have been used.')
                    if job.get('generation_provider') == 'openai' and not GENERATOR:
                        raise ValueError('Enable the OpenAI provider before retrying this portrait.')
                    if job['status'] in ACTIVE | {'awaiting_artwork', 'awaiting_review'}:
                        return self.send(200, public_job(job))
                    if job['status'] in ('uncertain', 'needs_photo'):
                        raise ValueError('This attempt needs a studio review or a different photo before retrying.')
                    feedback = body.get('feedback', '')
                    if feedback and feedback not in FEEDBACK:
                        raise ValueError('Choose an available correction.')
                    job['feedback'] = feedback
                    prepare_generation(job)
                    if job.get('generation_provider') == 'openai':
                        start_generation(job)
                    else:
                        job['status'], job['error'] = 'awaiting_artwork', None
                        save_json(job_path(job['id']) / 'job.json', job)
                    return self.send(200, public_job(job))
                if path == '/api/orders':
                    job = self.owned_job(str(body.get('job_id', '')), session)
                    candidate = next((c for c in job['candidates'] if c['id'] == body.get('candidate_id')), None)
                    if not candidate or candidate.get('review_status', 'approved') != 'approved' or body.get('approved') is not True:
                        raise ValueError('Approve an available portrait before placing your test order.')
                    product, size = body.get('product'), body.get('size')
                    totals = quote(product, size)
                    key = body.get('key', '')
                    if not isinstance(key, str) or not ID.fullmatch(key):
                        raise ValueError('Invalid checkout reference.')
                    file = DATA / 'orders' / f'{key}.json'
                    if file.exists():
                        order = read_json(file)
                        if order['session'] != session or (order['job_id'], order['candidate']['id'], order['product'], order['size']) != (job['id'], candidate['id'], product, size):
                            raise ValueError('Checkout reference was already used. Start a new checkout.')
                        return self.send(200, {k:v for k,v in order.items() if k != 'session'})
                    order = {'id': key, 'number': 'MH-' + key[:6].upper(), 'session': session, 'job_id': job['id'], 'name': job['name'], 'style': job['style'], 'demo': job['demo'], 'candidate': candidate, 'product': product, 'size': size, 'totals': totals, 'created': time.time(), 'status': 'digital_ready' if product == 'digital' else 'awaiting_review', 'test': True}
                    save_json(file, order)
                    return self.send(201, {k:v for k,v in order.items() if k != 'session'})
                match = re.fullmatch(r'/api/orders/([a-f0-9]{24})/advance', path)
                if match:
                    file = DATA / 'orders' / f'{match[1]}.json'
                    order = read_json(file)
                    if order['session'] != session:
                        raise FileNotFoundError()
                    stages = {'awaiting_review': 'in_production', 'in_production': 'shipped', 'shipped': 'delivered'}
                    order['status'] = stages.get(order['status'], order['status'])
                    save_json(file, order)
                    return self.send(200, {k:v for k,v in order.items() if k != 'session'})
            raise FileNotFoundError()
        except PermissionError as exc:
            self.send(403, {'error': str(exc)})
        except (FileNotFoundError, KeyError):
            self.send(404, {'error': 'This item was not found.'})
        except (ValueError, TypeError) as exc:
            self.send(400, {'error': str(exc) or 'Invalid request.'})
        except OSError:
            self.send(500, {'error': 'The local studio could not save your work. Check available disk space and try again.'})


def main():
    global GENERATOR, REVIEWER, DAILY_BUDGET_CENTS, PUBLIC_ORIGIN
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4187)
    args = parser.parse_args()
    PUBLIC_ORIGIN = os.environ.get('MINHWA_PUBLIC_ORIGIN', '')
    if PUBLIC_ORIGIN and not re.fullmatch(r'https://[a-z0-9]+(?:[.-][a-z0-9]+)*', PUBLIC_ORIGIN):
        parser.error('MINHWA_PUBLIC_ORIGIN must be an HTTPS origin without a path or port.')
    config = settings(ROOT)
    provider = config.get('MINHWA_IMAGE_PROVIDER', 'manual')
    if provider not in ('manual', 'openai'):
        parser.error('MINHWA_IMAGE_PROVIDER must be manual or openai.')
    if provider == 'openai':
        GENERATOR = OpenAIImages(config.get('OPENAI_API_KEY'), config.get('OPENAI_IMAGE_MODEL', 'gpt-image-2.6-sunburst'))
        REVIEWER = OpenAIReview(config.get('OPENAI_API_KEY'), config.get('OPENAI_REVIEW_MODEL', 'gpt-5-mini'))
    DAILY_BUDGET_CENTS = int(config.get('MINHWA_DAILY_BUDGET_CENTS', '1500'))
    if DAILY_BUDGET_CENTS < 0:
        parser.error('Daily budget must not be negative.')
    DATA.mkdir(parents=True, exist_ok=True)
    DATA.chmod(0o700)
    # One process owns the worker; queued files survive restarts on persistent disk.
    instance = (DATA / '.worker.lock').open('a')
    try:
        fcntl.flock(instance, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error('Another studio is already using this data directory.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Minhwa Studio: http://127.0.0.1:{args.port}', flush=True)
    print('OpenAI generation enabled; new uploads use API credits. Checkout is simulated.' if GENERATOR else 'Manual Codex generation. Checkout is simulated.', flush=True)
    recover_jobs()
    STOP.clear()
    if GENERATOR:
        threading.Thread(target=worker_loop, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        STOP.set()
        WAKE.set()
        server.server_close()

if __name__ == '__main__':
    main()
