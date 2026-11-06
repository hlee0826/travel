"""Produce a credential-free source bundle with the same explicit runtime allowlist."""
from pathlib import Path
import tarfile
import runpy
import io
root=Path(__file__).resolve().parent.parent
runpy.run_path(str(root/'deploy/prepare_vercel.py'))
files=[root/name for name in ('server.py','generation.py','artifacts.py','pyproject.toml','uv.lock','vercel.json')]
for directory in ('app','hosted','hosted_web','fonts'):
    files.extend(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not any(part.startswith('.') for part in p.relative_to(root).parts))
files.extend([root/'minhwa_workflow/__init__.py',root/'minhwa_workflow/workflow.py'])
files.extend((root/'minhwa_workflow/style-anchors').glob('*.png'))
assert len(list((root/'minhwa_workflow/style-anchors').glob('*.png')))==4
assert (root/'hosted_web/upload.js').is_file()
for file in files:
    assert file.is_file() and not file.is_symlink()
    assert '.env' not in file.name and '.studio' not in file.parts
(root/'dist').mkdir(exist_ok=True)
with tarfile.open(root/'dist/minhwa-vercel-source.tar.gz','w:gz') as archive:
    # The release is already allowlisted; root-level wildcard negations drop nested files in Vercel.
    ignore=b'**/__pycache__/**\n.env*\n'
    info=tarfile.TarInfo('.vercelignore'); info.size=len(ignore)
    archive.addfile(info,io.BytesIO(ignore))
    for file in sorted(set(files)):
        archive.add(file,arcname=str(file.relative_to(root)),recursive=False)
print(f'Credential-free Vercel source bundle prepared ({len(set(files))} runtime files).')
