import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.catalog = {'version': 1, 'styles': {}}
        for style in ('peony', 'lotus'):
            self.catalog['styles'][style] = {}
            for bucket in workflow.BUCKETS:
                name = f'{style}-{bucket}.png'
                (self.root / name).write_bytes(b'PNG fixture ' + name.encode())
                self.catalog['styles'][style][bucket] = {'status': 'ready', 'references': [name]}
        self.catalog_path = self.root / 'reference-catalog.json'
        self.save_catalog()
        self.source = self.root / 'source.png'
        self.source.write_bytes(b'original photo')
        for target, value in [('REFERENCE_ROOT', self.root), ('CATALOG_PATH', self.catalog_path)]:
            patcher = patch.object(workflow, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def save_catalog(self):
        self.catalog_path.write_text(json.dumps(self.catalog))

    def test_all_eight_buckets_select_only_their_garden_references(self):
        self.assertEqual(len(workflow.BUCKETS), 8)
        for style in ('peony', 'lotus'):
            for bucket in workflow.BUCKETS:
                with self.subTest(style=style, bucket=bucket):
                    inputs = workflow.generation_inputs(self.source, style, bucket)
                    self.assertEqual(inputs['referenced_image_paths'], [str(self.source), str(self.root / f'{style}-{bucket}.png')])
                    self.assertEqual(len(inputs['reference_hashes']), 2)
                    self.assertIn('IDENTITY ONLY', inputs['prompt'])
                    self.assertEqual(inputs['bucket'], bucket)
                    if bucket.endswith('_front'):
                        self.assertIn('looking forward', inputs['composition'])
                        self.assertNotIn('aimed at', inputs['composition'])
                    else:
                        self.assertIn('aimed at one nearby butterfly', inputs['composition'])
                    if bucket.startswith('portrait_'):
                        self.assertIn('do not invent a lower body', inputs['composition'])

    def test_pending_missing_and_invalid_references_fail_closed(self):
        for style, bucket in [('other', 'standing_front'), ('peony', 'other')]:
            with self.assertRaises(ValueError):
                workflow.generation_inputs(self.source, style, bucket)
        entry = self.catalog['styles']['peony']['standing_front']
        entry['status'] = 'pending'
        self.save_catalog()
        with self.assertRaises(workflow.ReferenceUnavailable):
            workflow.generation_inputs(self.source, 'peony', 'standing_front')
        entry['status'] = 'ready'
        for files in ([], ['missing.png'], ['../escape.png'], ['/tmp/escape.png'], ['source.png'] * 2, ['source.png'] * 3):
            entry['references'] = files
            self.save_catalog()
            with self.subTest(files=files), self.assertRaises(ValueError):
                workflow.generation_inputs(self.source, 'peony', 'standing_front')

    def test_saved_selection_survives_catalog_changes_and_detects_asset_changes(self):
        inputs = workflow.generation_inputs(self.source, 'peony', 'standing_front')
        self.catalog['styles']['peony']['standing_front']['references'] = ['lotus-sitting_profile.png']
        self.save_catalog()
        moved = self.root / 'moved-source.png'
        moved.write_bytes(self.source.read_bytes())
        restored = workflow.restore_inputs(moved, inputs)
        self.assertEqual(restored['prompt'], inputs['prompt'])
        self.assertEqual(restored['referenced_image_paths'][1:], inputs['referenced_image_paths'][1:])
        Path(restored['referenced_image_paths'][1]).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'reference changed'):
            workflow.restore_inputs(moved, inputs)

    def test_cli_requires_explicit_bucket_and_preserves_existing_output(self):
        script = self.root / 'workflow.py'
        shutil.copyfile(workflow.__file__, script)
        anchors = self.root / 'style-anchors'
        anchors.mkdir()
        shutil.copyfile(self.root / 'peony-standing_front.png', anchors / 'peony-standing_front.png')
        output = self.root / 'inputs.json'
        command = [sys.executable, str(script), '--source', str(self.source), '--style', 'peony', '--output', str(output)]
        self.assertNotEqual(subprocess.run(command, cwd='/', capture_output=True).returncode, 0)
        command += ['--bucket', 'standing_front']
        result = subprocess.run(command, cwd='/', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = output.read_bytes()
        self.assertEqual(json.loads(before)['bucket'], 'standing_front')
        self.assertNotEqual(subprocess.run(command, cwd='/', capture_output=True).returncode, 0)
        self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
