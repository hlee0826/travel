"""Checkpoint every paid call before sending it; ambiguous calls require an operator."""
import hashlib
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from psycopg.types.json import Jsonb
from hosted import db, storage
from hosted.config import required, generation_enabled
from generation import OpenAIImages, OpenAIReview, IMAGE_SIZE, ART_FIELDS, IDENTITY_FIELDS
from artifacts import artwork_files, matted_print
from minhwa_workflow.workflow import generation_inputs, identity_inputs
from server import image_bytes, FEEDBACK

STAGES = ('checking_photo', 'painting_identity', 'checking_identity',
          'painting_integrated', 'checking_artwork', 'rendering')


def render_files(doc, attempt):
    raw = storage.read('art', f'{doc["id"]}/{attempt}/artwork.png')
    files = artwork_files(raw, doc['name'])
    files['print-12x16.png'] = matted_print(files['master.png'])
    for name, data in files.items():
        storage.put('art', f'{doc["id"]}/{attempt}/{name}', data, 'image/jpeg' if name.endswith('.jpg') else 'image/png')
    return {'id':attempt, 'url':f'/media/{doc["id"]}/art-{attempt}.png',
            'dimensions':list(IMAGE_SIZE), 'artifacts_version':1, 'review_status':'approved',
            'master_sha256':hashlib.sha256(files['master.png']).hexdigest()}


def perform(doc, attempt, stage, previous):
    if stage == 'rendering':
        return {'candidate':render_files(doc, attempt)}
    with tempfile.TemporaryDirectory(prefix='minhwa-') as directory:
        source = Path(directory)/'source.png'
        source.write_bytes(storage.read('art', doc['id']+'/source.png'))
        if hashlib.sha256(source.read_bytes()).hexdigest() != doc['source_hash']:
            raise ValueError('Source integrity check failed.')
        review = OpenAIReview(required('OPENAI_API_KEY'), os.environ.get('OPENAI_REVIEW_MODEL','gpt-5-mini'))
        if stage == 'checking_photo':
            verdict, metadata = review.photo(source, doc['session'])
            return {'verdict':verdict, 'metadata':metadata}
        photo = previous['checking_photo']['verdict']
        identity = photo['identity'] + '\nUnseen or uncertain: ' + photo['unseen_features']
        identity_request = identity_inputs(source, identity, FEEDBACK.get(doc.get('feedback'), ''))
        if stage == 'painting_identity':
            raw, metadata = OpenAIImages(required('OPENAI_API_KEY'), os.environ.get('OPENAI_IMAGE_MODEL','gpt-image-2.6-sunburst')).generate(identity_request, doc['session'])
            raw, dimensions = image_bytes(raw)
            if dimensions != IMAGE_SIZE or hashlib.sha256(raw).hexdigest() == doc['source_hash']:
                raise ValueError('Identity study integrity check failed.')
            storage.put('art', f'{doc["id"]}/{attempt}/identity-study.png', raw)
            return {'metadata':metadata, 'reference_hashes':identity_request['reference_hashes']}
        if identity_request['reference_hashes'] != previous['painting_identity']['reference_hashes']:
            raise ValueError('Identity reference integrity check failed.')
        study = Path(directory)/'identity-study.png'
        study.write_bytes(storage.read('art', f'{doc["id"]}/{attempt}/identity-study.png'))
        if stage == 'checking_identity':
            verdict, metadata = review.identity_study(source, study, identity, doc['session'])
            return {'verdict':verdict, 'metadata':metadata,
                    'identity_hash':hashlib.sha256(study.read_bytes()).hexdigest()}
        approved_study = Path(directory)/'approved-identity-study.png'
        approved_study.write_bytes(storage.read('art', f'{doc["id"]}/identity-study.png'))
        if hashlib.sha256(approved_study.read_bytes()).hexdigest() != doc.get('identity_study_hash'):
            raise ValueError('Approved identity study integrity check failed.')
        inputs = generation_inputs(approved_study, doc['style'], identity, FEEDBACK.get(doc.get('feedback'), ''))
        if stage == 'painting_integrated':
            raw, metadata = OpenAIImages(required('OPENAI_API_KEY'), os.environ.get('OPENAI_IMAGE_MODEL','gpt-image-2.6-sunburst')).generate(inputs, doc['session'])
            raw, dimensions = image_bytes(raw)
            if dimensions != IMAGE_SIZE or hashlib.sha256(raw).hexdigest() == doc['source_hash']:
                raise ValueError('Artwork integrity check failed.')
            storage.put('art', f'{doc["id"]}/{attempt}/artwork.png', raw)
            return {'metadata':metadata, 'reference_hashes':inputs['reference_hashes']}
        if inputs['reference_hashes'] != previous['painting_integrated']['reference_hashes']:
            raise ValueError('Reference integrity check failed.')
        artwork = Path(directory)/'artwork.png'
        artwork.write_bytes(storage.read('art', f'{doc["id"]}/{attempt}/artwork.png'))
        verdict, metadata = review.artwork(source, artwork, inputs['referenced_image_paths'][1:], doc['style'], identity, doc['session'])
        return {'verdict':verdict, 'metadata':metadata}


def run_stage(job_id, attempt, stage):
    if stage not in STAGES:
        raise ValueError('Unknown stage.')
    if not generation_enabled():
        return 'paused'
    claim = secrets.token_hex(16)
    with db.connect() as conn:
        doc = db.job(conn, job_id, lock=True)['document']
        if doc.get('attempt_id') != attempt:
            return 'stopped'
        rows = conn.execute('SELECT * FROM minhwa.steps WHERE attempt_id=%s', (attempt,)).fetchall()
        steps = {r['name']:r for r in rows}
        current = steps.get(stage)
        if current and current['status'] == 'completed':
            if stage == 'checking_identity' and doc.get('identity_study_status') == 'approved':
                return 'continue'
            return current['result']['outcome']
        if doc['status'] in ('ready','uncertain','awaiting_review','awaiting_identity_approval','needs_photo','rejected','failed'):
            return 'stopped'
        if current:
            if current['status'] == 'running' and (datetime.now(timezone.utc)-current['started']).total_seconds() < 600:
                return 'busy'
            doc.update(status='uncertain', error='This attempt was interrupted. The studio must check it before another is started.')
            db.save_job(conn, doc)
            conn.execute("UPDATE minhwa.steps SET status='uncertain' WHERE attempt_id=%s AND name=%s", (attempt,stage))
            conn.execute("UPDATE minhwa.attempts SET status='uncertain' WHERE id=%s", (attempt,))
            return 'stopped'
        previous = {name:row['result'] for name,row in steps.items() if row['status']=='completed'}
        if doc.get('identity_study_status') == 'approved' and 'checking_identity' in previous:
            previous['checking_identity'] = {**previous['checking_identity'], 'outcome':'continue'}
        if any(name not in previous or previous[name]['outcome'] != 'continue' for name in STAGES[:STAGES.index(stage)]):
            return 'stopped'
        conn.execute("INSERT INTO minhwa.steps(attempt_id,name,status,claim) VALUES(%s,%s,'running',%s)", (attempt,stage,claim))
        doc.update(status=stage)
        db.save_job(conn, doc)
        conn.execute("UPDATE minhwa.attempts SET status='running' WHERE id=%s", (attempt,))
    try:
        result = perform(doc, attempt, stage, previous)
    except Exception:
        # Never log provider exceptions, request bodies, signed links, or credentials.
        with db.connect() as conn:
            current_doc = db.job(conn, job_id, lock=True)['document']
            if current_doc.get('attempt_id') == attempt:
                current_doc.update(status='uncertain', error='The studio needs to check this attempt before another is started.')
                db.save_job(conn, current_doc)
            conn.execute("UPDATE minhwa.steps SET status='uncertain' WHERE attempt_id=%s AND name=%s AND claim=%s", (attempt,stage,claim))
            conn.execute("UPDATE minhwa.attempts SET status='uncertain' WHERE id=%s", (attempt,))
        return 'stopped'
    with db.connect() as conn:
        doc = db.job(conn, job_id, lock=True)['document']
        row = conn.execute('SELECT status,claim FROM minhwa.steps WHERE attempt_id=%s AND name=%s FOR UPDATE', (attempt,stage)).fetchone()
        if doc.get('attempt_id') != attempt or row['claim'] != claim or row['status'] != 'running':
            return 'stopped'
        outcome = 'continue'
        if stage == 'checking_photo':
            v = result['verdict']
            if not (v['usable'] and v['pet_count']==1 and v['species'].lower() in ('cat','dog') and v['face_visible'] and v['details_clear']):
                doc.update(status='needs_photo', error='Please choose a clear photo of one cat or dog with its face visible.')
                outcome = 'stopped'
        elif stage == 'checking_identity':
            if not all(result['verdict'].get(k) is True for k in IDENTITY_FIELDS if k != 'reason'):
                doc.update(status='rejected', identity_study_status='failed_qa',
                           error='The identity study did not pass likeness and material checks. Request another interpretation.')
            else:
                raw = storage.read('art', f'{doc["id"]}/{attempt}/identity-study.png')
                storage.put('art', f'{doc["id"]}/identity-study.png', raw)
                doc.update(status='awaiting_identity_approval', error=None,
                           identity_study_status='pending',
                           identity_study=f'/media/{doc["id"]}/identity-study.png',
                           identity_study_hash=result['identity_hash'])
            outcome = 'stopped'
        elif stage == 'checking_artwork':
            if not all(result['verdict'].get(k) is True for k in ART_FIELDS if k != 'reason'):
                doc.update(status='awaiting_review')
                outcome = 'stopped'
        elif stage == 'rendering':
            doc['candidates'].append(result['candidate'])
            doc.update(status='ready', error=None, completed_batches=doc['completed_batches']+1)
            outcome = 'ready'
        result['outcome'] = outcome
        conn.execute("UPDATE minhwa.steps SET status='completed',result=%s WHERE attempt_id=%s AND name=%s", (Jsonb(result),attempt,stage))
        if outcome != 'continue':
            conn.execute('UPDATE minhwa.attempts SET status=%s WHERE id=%s', (doc['status'],attempt))
        db.save_job(conn, doc)
    return outcome
