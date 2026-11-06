import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import workflow


class WorkflowTests(unittest.TestCase):
    def test_roles_compositions_and_reference_files(self):
        # A bundled painting stands in for a photo; no private fixture is needed.
        source = workflow.STYLE_ANCHORS[0]
        for style, primary in [('peony', 'images 2 and 3'), ('lotus', 'image 4')]:
            inputs = workflow.generation_inputs(source, style)
            self.assertEqual(inputs['referenced_image_paths'], [str(source), *map(str, workflow.STYLE_ANCHORS)])
            self.assertIn(f'Use {primary} as the primary composition', inputs['prompt'])
            self.assertIn('IDENTITY ONLY', inputs['prompt'])
            self.assertIn('STYLE AND COMPOSITION ANCHORS', inputs['prompt'])
            self.assertFalse(inputs['transparent_background'])
            for path in inputs['referenced_image_paths']:
                self.assertTrue(Path(path).is_absolute())
                self.assertEqual(Path(path).read_bytes()[:8], b'\x89PNG\r\n\x1a\n')

    def test_two_photo_roles_are_explicit_and_ordered(self):
        face, body = workflow.STYLE_ANCHORS[:2]
        inputs = workflow.generation_inputs(face, 'peony', body_source=body)
        self.assertEqual(inputs['referenced_image_paths'], [str(face), str(body), *map(str, workflow.STYLE_ANCHORS)])
        self.assertEqual(len(inputs['reference_hashes']), 6)
        self.assertIn('Image 1 is the FACE IDENTITY photo', inputs['prompt'])
        self.assertIn('Image 2 is the FULL-BODY IDENTITY photo', inputs['prompt'])
        self.assertIn('distinctive facial expression', inputs['prompt'])
        self.assertIn('images 3 and 4 as the primary composition', inputs['prompt'])

    def test_invalid_style_or_missing_image_fails(self):
        with self.assertRaises(ValueError):
            workflow.generation_inputs(workflow.STYLE_ANCHORS[0], 'unknown')
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / 'missing.png'
            with self.assertRaisesRegex(ValueError, 'reference is missing'):
                workflow.generation_inputs(missing, 'peony')
            source = workflow.STYLE_ANCHORS[0]
            with patch.object(workflow, 'STYLE_ANCHORS', (missing,)):
                with self.assertRaisesRegex(ValueError, 'reference is missing'):
                    workflow.generation_inputs(source, 'lotus')

    def test_cli_runs_outside_repo_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'run' / 'inputs.json'
            command = [sys.executable, str(Path(workflow.__file__).resolve()),
                       '--source', str(workflow.STYLE_ANCHORS[0]), '--style', 'lotus',
                       '--output', str(output)]
            result = subprocess.run(command, cwd=temp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            before = output.read_bytes()
            self.assertEqual(len(json.loads(before)['referenced_image_paths']), 5)
            duplicate = subprocess.run(command, cwd=temp, capture_output=True, text=True)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
