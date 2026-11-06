"""Build an authenticated asset tree; never deploy Vercel's public/ bypass."""
from pathlib import Path
import shutil
root = Path(__file__).resolve().parent.parent
shutil.rmtree(root/'hosted_web', ignore_errors=True)
shutil.copytree(root/'public', root/'hosted_web', ignore=shutil.ignore_patterns('.*'))
assert not list((root/'hosted_web').rglob('.env*'))
print('Private web asset bundle prepared.')
