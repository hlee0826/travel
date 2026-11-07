import hashlib
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from PIL import Image
from generation import OpenAIReview, PHOTO_FIELDS, ART_FIELDS
from minhwa_workflow import workflow
from hosted import pipeline
from pose_fixtures import ready_references


def response(verdict):
    return {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(verdict)}]}]}


class PoseReviewTests(unittest.TestCase):
    def test_compact_schema_accepts_eight_buckets_and_rejects_invalid_output(self):
        reviewer = OpenAIReview('fake')
        for bucket in workflow.BUCKETS:
            verdict = {'usable': True, 'bucket': bucket, 'reason': ''}
            with patch('generation.request_json', return_value=(response(verdict), 'req')) as request, patch('generation.image_url', return_value='data:test'):
                self.assertEqual(reviewer.photo('source', 'session')[0], verdict)
                payload = request.call_args.args[2]
                schema = payload['text']['format']['schema']
                self.assertEqual(set(schema['properties']), {'usable', 'bucket', 'reason'})
                self.assertEqual(schema['properties']['bucket']['enum'], [*workflow.BUCKETS, None])
                self.assertEqual(len(payload['input'][0]['content']), 2)
                self.assertEqual(request.call_count, 1)
        for verdict in ({'usable': True, 'bucket': 'other', 'reason': ''},
                        {'usable': 'true', 'bucket': 'sitting_front', 'reason': ''},
                        {'usable': True, 'bucket': None},
                        {'usable': True, 'bucket': None, 'reason': 'x'*301},
                        {'usable': True, 'bucket': None, 'reason': '', 'identity': 'dog'}):
            with self.subTest(verdict=verdict), patch('generation.request_json', return_value=(response(verdict), None)):
                with self.assertRaises(ValueError):
                    reviewer.analyze([], 'check', PHOTO_FIELDS, 'session')
        self.assertFalse(workflow.photo_usable({'usable': True, 'bucket': None, 'reason': 'Pose unclear.'}))
        self.assertFalse(workflow.photo_usable({'usable': False, 'bucket': None, 'reason': 'Two pets.'}))

    def test_art_review_receives_selected_composition_and_variable_reference_count(self):
        with patch.object(OpenAIReview, 'analyze', return_value=({}, {})) as analyze:
            for bucket in workflow.BUCKETS:
                direction = workflow.composition(bucket)
                OpenAIReview('fake').artwork('photo', 'art', ['one-reference'], 'lotus', direction, 'session')
                args = analyze.call_args.args
                self.assertEqual(args[0], ['photo', 'art', 'one-reference'])
                self.assertIn(direction, args[1])
                self.assertNotIn('images 3-6', args[1])
                self.assertEqual(args[2], ART_FIELDS)

    def test_hosted_perform_persists_selection_without_reclassifying_or_reselecting(self):
        with ready_references() as root:
            raw = (root / 'peony/standing_front.png').read_bytes()
            doc = {'id': 'a'*24, 'session': 'test', 'style': 'peony', 'source_hash': hashlib.sha256(raw).hexdigest()}
            art = io.BytesIO()
            Image.new('RGB', pipeline.IMAGE_SIZE, 'green').save(art, 'PNG')
            objects = {doc['id'] + '/source.png': raw}
            def put(bucket, key, data, mime='image/png'):
                objects[key] = data
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'fake'}), patch('hosted.storage.read', side_effect=lambda b,k: objects[k]), patch('hosted.storage.put', side_effect=put), patch('hosted.pipeline.OpenAIReview') as reviewer, patch('hosted.pipeline.OpenAIImages') as generator:
                reviewer.return_value.photo.return_value = ({'usable': True, 'bucket': 'standing_front', 'reason': ''}, {})
                reviewer.return_value.artwork.return_value = ({k: True for k in ART_FIELDS}, {})
                generator.return_value.generate.return_value = (art.getvalue(), {})
                checked = pipeline.perform(doc, 'attempt', 'checking_photo', {})
                catalog = json.loads(workflow.CATALOG_PATH.read_text())
                catalog['styles']['peony']['standing_front']['references'] = ['lotus/sitting_profile.png']
                workflow.CATALOG_PATH.write_text(json.dumps(catalog))
                previous = {'checking_photo': checked}
                previous['painting'] = pipeline.perform(doc, 'attempt', 'painting', previous)
                pipeline.perform(doc, 'attempt', 'checking_artwork', previous)
                sent = generator.return_value.generate.call_args.args[0]
                self.assertEqual(sent['reference_files'], ['peony/standing_front.png'])
                self.assertEqual(reviewer.return_value.photo.call_count, 1)
                self.assertEqual(reviewer.return_value.artwork.call_args.args[4], checked['inputs']['composition'])
                self.assertEqual(len(reviewer.return_value.artwork.call_args.args[2]), 1)
                (root / 'peony/standing_front.png').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'reference changed'):
                    pipeline.perform(doc, 'attempt', 'checking_artwork', previous)

    def test_hosted_pending_and_unmatched_photos_do_not_prepare_painting(self):
        with ready_references() as root:
            raw = (root / 'peony/standing_front.png').read_bytes()
            doc = {'id': 'a'*24, 'session': 'test', 'style': 'peony', 'source_hash': hashlib.sha256(raw).hexdigest()}
            catalog = json.loads(workflow.CATALOG_PATH.read_text())
            catalog['styles']['peony']['standing_front']['status'] = 'pending'
            workflow.CATALOG_PATH.write_text(json.dumps(catalog))
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'fake'}), patch('hosted.storage.read', return_value=raw), patch('hosted.pipeline.OpenAIReview') as reviewer, patch('hosted.pipeline.OpenAIImages') as generator:
                reviewer.return_value.photo.return_value = ({'usable': True, 'bucket': 'standing_front', 'reason': ''}, {})
                result = pipeline.perform(doc, 'attempt', 'checking_photo', {})
                self.assertIn('unavailable', result)
                self.assertNotIn('inputs', result)
                reviewer.return_value.photo.return_value = ({'usable': True, 'bucket': None, 'reason': 'Unclear pose.'}, {})
                result = pipeline.perform(doc, 'attempt', 'checking_photo', {})
                self.assertNotIn('inputs', result)
                self.assertNotIn('unavailable', result)
                generator.assert_not_called()
