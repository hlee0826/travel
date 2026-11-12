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
        source = workflow.GARDEN_ANCHORS['peony'][0]
        for style in workflow.GARDENS:
            inputs = workflow.generation_inputs(source, style)
            self.assertEqual(inputs['referenced_image_paths'], [str(source.resolve()), *map(str, workflow.GARDEN_ANCHORS[style])])
            self.assertEqual(len(inputs['referenced_image_paths']), 7)
            self.assertEqual(len(inputs['reference_files']), 6)
            self.assertEqual(inputs['reference_roles'], list(workflow.REFERENCE_ROLES))
            self.assertIn(workflow.GARDENS[style]['label'], inputs['prompt'])
            self.assertIn('CUSTOMER IDENTITY AND POSE AUTHORITY', inputs['prompt'])
            self.assertIn('ART REFERENCES only', inputs['prompt'])
            self.assertIn('Preserve the source head angle and gaze', inputs['prompt'])
            self.assertIn('Do not force the pet to look at', inputs['prompt'])
            self.assertIn('Images 2-3 are direct-to-viewer calibration plates', inputs['prompt'])
            self.assertFalse(inputs['transparent_background'])
            for path in inputs['referenced_image_paths']:
                self.assertTrue(Path(path).is_absolute())
                self.assertGreater(Path(path).stat().st_size, 1000)
        self.assertIn('one to three small butterflies', workflow.generation_inputs(source, 'peony')['prompt'])
        self.assertIn('shallow water rhythm', workflow.generation_inputs(source, 'lotus')['prompt'])
        self.assertIn('exactly one Korean magpie', workflow.generation_inputs(source, 'pine')['prompt'])
        self.assertIn('Include no butterflies, peonies, or lotus', workflow.generation_inputs(source, 'pine')['prompt'])

    def test_each_garden_balances_direct_and_interaction_poses(self):
        expected_direct_anchors = {
            'peony': ('cat-16-peony-butterflies.jpg', 'dog-21-peony-butterflies.jpg'),
            'lotus': ('cat-17-lotus-butterflies.jpg', 'dog-22-lotus-butterflies.jpg'),
            'pine': ('cat-18-pine-magpie.jpg', 'dog-23-pine-magpie.jpg'),
        }
        for garden, direct_names in expected_direct_anchors.items():
            names = tuple(path.name for path in workflow.GARDEN_ANCHORS[garden])
            self.assertEqual(names[:2], direct_names)
            self.assertEqual(sum(name.startswith('cat-') for name in names), 3)
            self.assertEqual(sum(name.startswith('dog-') for name in names), 3)

    def test_invalid_style_or_missing_image_fails(self):
        with self.assertRaises(ValueError):
            workflow.generation_inputs(workflow.GARDEN_ANCHORS['peony'][0], 'unknown')
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / 'missing.png'
            with self.assertRaisesRegex(ValueError, 'reference is missing'):
                workflow.generation_inputs(missing, 'peony')
            source = workflow.GARDEN_ANCHORS['peony'][0]
            with patch.dict(workflow.GARDEN_ANCHORS, {'lotus': (missing,)}):
                with self.assertRaisesRegex(ValueError, 'reference is missing'):
                    workflow.generation_inputs(source, 'lotus')

    def test_cli_runs_outside_repo_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'run' / 'inputs.json'
            command = [sys.executable, str(Path(workflow.__file__).resolve()),
                       '--source', str(workflow.GARDEN_ANCHORS['peony'][0]), '--style', 'pine',
                       '--output', str(output)]
            result = subprocess.run(command, cwd=temp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            before = output.read_bytes()
            self.assertEqual(len(json.loads(before)['referenced_image_paths']), 7)
            duplicate = subprocess.run(command, cwd=temp, capture_output=True, text=True)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
