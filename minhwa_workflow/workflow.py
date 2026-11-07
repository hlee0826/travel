"""Minhwa v5: face and full-body identity photos plus four style anchors."""
import argparse
import json
import hashlib
from pathlib import Path

WORKFLOW_VERSION = 'minhwa-anchors-v5-two-photo-identity'
STYLE_ANCHORS = tuple(Path(__file__).resolve().parent / 'style-anchors' / name for name in (
    'peony-tuxedo-cat.png', 'peony-tabby-cat.png', 'lotus-corgi.png', 'bamboo-white-dog.png',
))


def generation_inputs(source, style, identity='', feedback='', body_source=None):
    """Prepare current two-photo inputs; ``None`` only supports archived pre-v5 jobs."""
    if style not in ('peony', 'lotus'):
        raise ValueError('Choose peony or lotus.')
    source = Path(source).expanduser().resolve()
    body_source = Path(body_source).expanduser().resolve() if body_source else None
    references = [source, *([body_source] if body_source else []), *STYLE_ANCHORS]
    for path in references:
        if not path.is_file():
            raise ValueError(f'Generation reference is missing: {path.name}. Restore it before generating.')
    offset = 1 if body_source else 0
    composition = (f'Use images {2 + offset} and {3 + offset} as the primary composition anchors: an upright pet, '
                   'asymmetric peony branches framing open paper, and scattered butterflies.'
                   if style == 'peony' else
                   f'Use image {4 + offset} as the primary composition anchor: a pet in side or three-quarter view, '
                   'lotus leaves and blossoms framing an open pond scene, and butterflies.')
    if body_source:
        role_copy = '''The six attached images have distinct roles. Image 1 is the FACE IDENTITY photo. It is the authority for head geometry, eye spacing and visible eye color, muzzle ratio, nose and mouth shape, ear carriage, age cues, and the pet's distinctive facial expression. Image 2 is the FULL-BODY IDENTITY photo. It is the authority for silhouette, body proportions, coat direction, color and marking placement, paws, tail, and characteristic posture. Images 3–6 are STYLE AND COMPOSITION ANCHORS, never pet identity references. If the identity photos appear to conflict because of angle or lighting, do not average them or invent a generic breed face: preserve the observable feature from the photo assigned to that role. Inspect both identity photos and all four anchors visually.
Image 3: tuxedo cat with peonies. Image 4: tabby cat with peonies. Image 5: corgi with lotus. Image 6: white dog among bamboo and broad leaves; use only its painted region, ignoring promotional text and outer margins.'''
        identity_copy = '''Take the pet's facial identity and expression ONLY from image 1. Take body shape, coat pattern and full-body identifying features ONLY from image 2. The photos must depict the same individual pet; never blend two animals. Do not borrow the cats' or dogs' identity, markings, color, or breed from images 3–6. Preserve the uploaded pet's exact recognizable identity while interpreting it as painted forms.'''
        source_numbers = 'images 1 and 2'
        anchor_numbers = '3–6'
        bamboo_number = '6'
    else:
        role_copy = '''The five attached images have distinct roles. Image 1 is the uploaded pet photograph: IDENTITY ONLY. Images 2–5 are STYLE AND COMPOSITION ANCHORS, never pet identity references. Inspect and use all four anchors visually, not merely their text descriptions.
Image 2: tuxedo cat with peonies. Image 3: tabby cat with peonies. Image 4: corgi with lotus. Image 5: white dog among bamboo and broad leaves; use only its painted region, ignoring promotional text and outer margins.'''
        identity_copy = '''Take ONLY the uploaded pet's ear silhouette, face and muzzle proportions, eye color, age, distinctive coat patches, and body proportions from image 1. Do not borrow the cats' or dogs' identity, markings, color, or breed from images 2–5. Preserve the uploaded pet's recognizable identity while interpreting it as painted forms.'''
        source_numbers = 'image 1'
        anchor_numbers = '2–5'
        bamboo_number = '5'
    prompt = f'''Create a wholly new 4:5 traditional Korean minhwa-inspired pet painting. Art direction: {WORKFLOW_VERSION}.
{role_copy}
{composition} All four anchors guide traditional pigment color, botanical drawing, paper texture, decorative flattened space, pet-to-plant scale, and calm negative space. Adapt their overall composition to a new scene; do not duplicate an anchor exactly or combine every motif into a cluttered collage.
Image {bamboo_number} additionally guides spacious botanical framing. {identity_copy}
Do not use {source_numbers} as a pixel base, edit target, tracing, background, or composition guide. Discard their settings and camera lighting. Do not use any previous generated portrait as a reference. This is fresh image synthesis, not a filtered photograph.
Create a coherent pose that preserves the pet's observable facial expression: eyelid openness, brow tension, mouth set, muzzle angle, and ear attitude. Do not replace it with a generic happy, smiling, or alert expression. A nearby butterfly may support the scene only when its placement follows the pet's natural gaze; never distort the face or redirect both eyes merely to force an interaction.
Match the anchors' traditional hand-painted visual language with matte mineral-pigment washes, deliberate fine ink contours, restrained shading, and subtly textured warm hanji paper. Simplify the pet's fur into grouped color masses with sparse brush accents. Keep less fur detail than a photograph; paint pet and plants consistently. Avoid glossy eyes, lens blur, camera lighting, photographic cutouts, paper filters over photo textures, airbrushed realism, and modern cartoon rendering.
Exactly one pet. Keep ears and visible paws within safe margins. Do not invent unseen identifying markings from a cropped source. Leave breathing room around the face and butterfly.
Do not copy any anchor's text, names, signatures, seals, watermarks, promotional borders, or frame. No text or stamps anywhere; the website adds the pet name separately. Images {anchor_numbers} never override identity evidence.
'''
    if identity:
        prompt += f'\nIdentity observations to verify against {source_numbers} (the photographs always take precedence if these notes are inaccurate; never invent the unseen):\n' + identity + '\n'
    if feedback:
        prompt += '\nCorrection priority for this fresh painting: ' + feedback + '\n'
    return {'prompt': prompt, 'referenced_image_paths': [str(p) for p in references], 'transparent_background': False,
            'reference_hashes': [hashlib.sha256(p.read_bytes()).hexdigest() for p in references]}


def main():
    parser = argparse.ArgumentParser(description='Prepare identity and style inputs for Codex image generation; no model API calls.')
    parser.add_argument('--source', type=Path, required=True, help='Pet face identity photo (PNG, JPEG, or WebP).')
    parser.add_argument('--body-source', type=Path, required=True,
                        help='Full-body identity photo of the same pet (required).')
    parser.add_argument('--style', choices=('peony', 'lotus'), default='peony')
    parser.add_argument('--output', type=Path, required=True, help='New JSON file; existing files are never overwritten.')
    args = parser.parse_args()
    try:
        inputs = generation_inputs(args.source, args.style, body_source=args.body_source)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(inputs, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
    print(f'Prepared {args.output.resolve()}')
    print(f'In Codex, inspect all {len(inputs["referenced_image_paths"])} images and pass this JSON to the built-in image generation tool.')


if __name__ == '__main__':
    main()
