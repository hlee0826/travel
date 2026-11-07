"""Eight pose buckets; only the selected garden and bucket supply references."""
import argparse
import hashlib
import json
from pathlib import Path

WORKFLOW_VERSION = 'minhwa-poses-v5'
REFERENCE_ROOT = Path(__file__).resolve().parent / 'style-anchors'
CATALOG_PATH = Path(__file__).resolve().parent / 'reference-catalog.json'
BUCKETS = tuple(f'{pose}_{view}' for pose in ('standing', 'sitting', 'reclining', 'portrait')
                for view in ('front', 'profile'))


class ReferenceUnavailable(ValueError):
    pass


def photo_usable(photo):
    if (not isinstance(photo, dict) or set(photo) != {'usable', 'bucket', 'reason'}
            or type(photo['usable']) is not bool or not isinstance(photo['reason'], str)
            or len(photo['reason']) > 300
            or (photo['bucket'] is not None and photo['bucket'] not in BUCKETS)):
        raise ValueError('The photo check did not return a complete assessment.')
    return photo['usable'] and photo['bucket'] in BUCKETS


def composition(bucket):
    if bucket not in BUCKETS:
        raise ValueError('Choose one of the eight pose buckets.')
    pose, view = bucket.split('_')
    framing = ('Use an intentional head-and-chest portrait crop; do not invent a lower body or paws.'
               if pose == 'portrait' else
               f'Keep the pet {pose}, with the body and paws comfortably inside the painting. Do not invent unseen identifying markings.')
    gaze = ('Keep the head and eyes looking forward toward the viewer. Butterflies may be decorative; do not turn the face toward one.'
            if view == 'front' else
            'Keep a profile-compatible head direction, with muzzle and visible pupils aimed at one nearby butterfly. Use only a modest adjustment, not a large head turn.')
    return framing + ' ' + gaze


def reference_paths(files):
    if (not isinstance(files, list) or not 1 <= len(files) <= 2
            or any(not isinstance(name, str) for name in files) or len(set(files)) != len(files)):
        raise ValueError('A reference set must contain one or two distinct image files.')
    paths = []
    for name in files:
        relative = Path(name)
        path = (REFERENCE_ROOT / relative).resolve()
        if (relative.is_absolute() or '..' in relative.parts
                or not path.is_relative_to(REFERENCE_ROOT.resolve())
                or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp')):
            raise ValueError('Invalid branch reference path.')
        if not path.is_file():
            raise ReferenceUnavailable('This composition is not available yet. The studio needs to add its reference images.')
        paths.append(path)
    return paths


def reference_set(style, bucket):
    if style not in ('peony', 'lotus') or bucket not in BUCKETS:
        raise ValueError('Choose an available garden and pose bucket.')
    catalog = json.loads(CATALOG_PATH.read_text())
    if catalog.get('version') != 1:
        raise ValueError('Unsupported reference catalog version.')
    entry = catalog['styles'][style][bucket]
    if entry.get('status') != 'ready' or not entry.get('references'):
        raise ReferenceUnavailable('This composition is not available yet. The studio needs to add its reference images.')
    return catalog['version'], entry['references'], reference_paths(entry['references'])


def branch_available(style, bucket):
    try:
        reference_set(style, bucket)
        return True
    except (ValueError, OSError, KeyError, TypeError):
        return False


def generation_inputs(source, style, bucket, feedback=''):
    direction = composition(bucket)
    catalog_version, files, anchors = reference_set(style, bucket)
    source = Path(source).expanduser().resolve()
    references = [source, *anchors]
    if not source.is_file():
        raise ValueError('The pet source photo is missing.')
    garden = ('asymmetric peony branches and blossoms' if style == 'peony' else 'lotus leaves and blossoms around an open pond')
    prompt = f'''Create a wholly new 4:5 traditional Korean minhwa-inspired pet painting. Art direction: {WORKFLOW_VERSION}. Selected pose: {bucket}.
Image 1 is the uploaded pet photograph: IDENTITY ONLY, plus evidence of the selected pose category. The remaining {len(anchors)} attached images are STYLE AND COMPOSITION ANCHORS, never pet identity references. Inspect every supplied anchor visually.
Paint {garden} with calm open paper. {direction}
Use the anchors for matte pigment color, botanical drawing, warm hanji paper, decorative flattened space, pet-to-plant scale, and negative space. Adapt the composition; do not duplicate an anchor.
Take the pet's recognizable ears, muzzle, age, visible eye color, coat patches, and proportions from image 1 only. Do not borrow reference animals' identity, breed, markings, or colors. Do not invent hidden identifying features.
Keep the selected posture and framing while making a fresh painted setting. Do not use image 1 as a pixel base, tracing, or photographic texture. Discard its room, background, and camera lighting. Never use a previous generated portrait as a reference.
Paint pet and plants consistently with matte mineral-pigment washes, deliberate ink contours, restrained shading, grouped fur color masses, and sparse brush accents. Avoid photographic cutouts, paper filters over photos, glossy realism, lens blur, airbrushing, and modern cartoons.
Exactly one pet. Keep ears and intentionally visible paws within safe margins. No copied text, names, signatures, seals, watermarks, promotional borders, or frame; the website adds the name separately.
'''
    if feedback:
        prompt += '\nCorrection priority: ' + feedback + '\n'
    return {'prompt': prompt, 'referenced_image_paths': list(map(str, references)),
            'transparent_background': False, 'workflow_version': WORKFLOW_VERSION,
            'catalog_version': catalog_version, 'style': style, 'bucket': bucket,
            'composition': direction, 'reference_files': files,
            'reference_hashes': [hashlib.sha256(p.read_bytes()).hexdigest() for p in references]}


def restore_inputs(source, saved):
    """Rebind temporary paths without reselecting references or rewriting the prompt."""
    if saved.get('workflow_version') != WORKFLOW_VERSION or saved.get('bucket') not in BUCKETS:
        raise ValueError('This attempt uses an older workflow. The studio must check it before continuing.')
    paths = [Path(source).resolve(), *reference_paths(saved['reference_files'])]
    if saved['reference_hashes'] != [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]:
        raise ValueError('A reference changed after this painting was prepared. The studio must check it before continuing.')
    return {**saved, 'referenced_image_paths': list(map(str, paths))}


def main():
    parser = argparse.ArgumentParser(description='Prepare inputs for one explicitly assessed pose bucket; no API calls.')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--style', choices=('peony', 'lotus'), default='peony')
    parser.add_argument('--bucket', choices=BUCKETS, required=True, help='Bucket selected after inspecting the photo.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        inputs = generation_inputs(args.source, args.style, args.bucket)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(inputs, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
    print(f'Prepared {args.output.resolve()}')
    print('Inspect and attach every image in referenced_image_paths, in order.')


if __name__ == '__main__':
    main()
