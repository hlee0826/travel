"""Minhwa v4: identity photo plus four style/composition anchors. Standard library only."""
import argparse
import json
import hashlib
from pathlib import Path

WORKFLOW_VERSION = 'minhwa-anchors-v4'
STYLE_ANCHORS = tuple(Path(__file__).resolve().parent / 'style-anchors' / name for name in (
    'peony-tuxedo-cat.png', 'peony-tabby-cat.png', 'lotus-corgi.png', 'bamboo-white-dog.png',
))


def generation_inputs(source, style, identity='', feedback=''):
    if style not in ('peony', 'lotus'):
        raise ValueError('Choose peony or lotus.')
    source = Path(source).expanduser().resolve()
    references = [source, *STYLE_ANCHORS]
    for path in references:
        if not path.is_file():
            raise ValueError(f'Generation reference is missing: {path.name}. Restore it before generating.')
    composition = ('Use images 2 and 3 as the primary composition anchors: an upright pet, '
                   'asymmetric peony branches framing open paper, and scattered butterflies.'
                   if style == 'peony' else
                   'Use image 4 as the primary composition anchor: a pet in side or three-quarter view, '
                   'lotus leaves and blossoms framing an open pond scene, and butterflies.')
    prompt = f'''Create a wholly new 4:5 traditional Korean minhwa-inspired pet painting. Art direction: {WORKFLOW_VERSION}.
The five attached images have distinct roles. Image 1 is the uploaded pet photograph: IDENTITY ONLY. Images 2–5 are STYLE AND COMPOSITION ANCHORS, never pet identity references. Inspect and use all four anchors visually, not merely their text descriptions.
Image 2: tuxedo cat with peonies. Image 3: tabby cat with peonies. Image 4: corgi with lotus. Image 5: white dog among bamboo and broad leaves; use only its painted region, ignoring promotional text and outer margins.
{composition} All four anchors guide traditional pigment color, botanical drawing, paper texture, decorative flattened space, pet-to-plant scale, and calm negative space. Image 5 additionally guides spacious botanical framing. Adapt their overall composition to a new scene; do not duplicate an anchor exactly or combine every motif into a cluttered collage.
Take ONLY the uploaded pet's ear silhouette, face and muzzle proportions, eye color, age, distinctive coat patches, and body proportions from image 1. Do not borrow the cats' or dogs' identity, markings, color, or breed from images 2–5. Preserve the uploaded pet's recognizable identity while interpreting it as painted forms.
Do not use image 1 as a pixel base, edit target, tracing, fixed pose, background, or composition guide. Discard its setting and camera lighting. Do not use any previous generated portrait as a reference. This is fresh image synthesis, not a filtered photograph.
Invent a coherent pose with the head lifted and turned toward one nearby butterfly just above and in front of the muzzle. Both pupils and the muzzle must point toward that same butterfly along a believable sightline. The pet interacts with the scene instead of staring at the camera.
Match the anchors' traditional hand-painted visual language with matte mineral-pigment washes, deliberate fine ink contours, restrained shading, and subtly textured warm hanji paper. Simplify the pet's fur into grouped color masses with sparse brush accents. Keep less fur detail than a photograph; paint pet and plants consistently. Avoid glossy eyes, lens blur, camera lighting, photographic cutouts, paper filters over photo textures, airbrushed realism, and modern cartoon rendering.
Exactly one pet. Keep ears and visible paws within safe margins. Do not invent unseen identifying markings from a cropped source. Leave breathing room around the face and butterfly.
Do not copy any anchor's text, names, signatures, seals, watermarks, promotional borders, or frame. No text or stamps anywhere; the website adds the pet name separately.
'''
    if identity:
        prompt += '\nIdentity observations to verify against image 1 (the photograph always takes precedence if these notes are inaccurate; never invent the unseen):\n' + identity + '\n'
    if feedback:
        prompt += '\nCorrection priority for this fresh painting: ' + feedback + '\n'
    return {'prompt': prompt, 'referenced_image_paths': [str(p) for p in references], 'transparent_background': False,
            'reference_hashes': [hashlib.sha256(p.read_bytes()).hexdigest() for p in references]}


def main():
    parser = argparse.ArgumentParser(description='Prepare five-image inputs for Codex image generation; no model API calls.')
    parser.add_argument('--source', type=Path, required=True, help='Pet identity photo (PNG, JPEG, or WebP).')
    parser.add_argument('--style', choices=('peony', 'lotus'), default='peony')
    parser.add_argument('--output', type=Path, required=True, help='New JSON file; existing files are never overwritten.')
    args = parser.parse_args()
    try:
        inputs = generation_inputs(args.source, args.style)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(inputs, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
    print(f'Prepared {args.output.resolve()}')
    print('In Codex, inspect all five images and pass this JSON to the built-in image generation tool.')


if __name__ == '__main__':
    main()
