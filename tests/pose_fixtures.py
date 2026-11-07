"""Temporary branch assets; never enable placeholder references in the real catalog."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from PIL import Image
from minhwa_workflow import workflow


@contextmanager
def ready_references():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        catalog = {'version': 1, 'styles': {}}
        for style in ('peony', 'lotus'):
            catalog['styles'][style] = {}
            for index, bucket in enumerate(workflow.BUCKETS):
                name = f'{style}/{bucket}.png'
                path = root / name
                path.parent.mkdir(exist_ok=True)
                Image.new('RGB', (100, 150), (index * 25, 20 if style == 'peony' else 80, 50)).save(path)
                catalog['styles'][style][bucket] = {'status': 'ready', 'references': [name]}
        path = root / 'catalog.json'
        path.write_text(json.dumps(catalog))
        with patch.object(workflow, 'REFERENCE_ROOT', root), patch.object(workflow, 'CATALOG_PATH', path):
            yield root
