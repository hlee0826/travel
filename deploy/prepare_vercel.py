"""Validate the tracked assets served exclusively through the application gate."""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
assert not (root/'public').exists(), 'public/ bypasses the application password gate'
assert (root/'hosted_web/index.html').is_file()
assert (root/'hosted_web/upload.js').is_file()
assert not list((root/'hosted_web').rglob('.env*'))
print('Private web assets verified.')
