"""Prepare one identity photo and six garden-specific minhwa art references."""
import argparse
import hashlib
import json
from pathlib import Path


WORKFLOW_VERSION = 'minhwa-gardens-v6'
ANCHOR_ROOT = Path(__file__).resolve().parent / 'garden-anchors'
REFERENCE_ROLES = (
    'overall garden composition and pet-to-motif scale',
    'quiet space and asymmetric edge framing',
    'traditional botanical or arboreal motif drawing',
    'hanji, matte pigment, fine ink contour, and unified pet-and-garden treatment',
    'mineral-pigment palette and restrained barim gradation',
    'shallow symbolic space and visual rhythm',
)
GARDENS = {
    'peony': {
        'label': 'Peony & Butterfly Garden',
        'korean': '모란과 나비',
        'meaning': 'flourishing affection, beauty, and celebration',
        'references': (
            'cat-16-peony-butterflies.jpg', 'dog-21-peony-butterflies.jpg',
            'cat-02-peony-butterflies.jpg', 'dog-02-peony-butterflies.jpg',
            'cat-03-peony-butterflies.jpg', 'dog-03-peony-butterflies.jpg',
        ),
        'recipe': ('Use one restrained peony branch or flower mass entering from an edge and '
                   'one to three small butterflies as subordinate movement elements. Do not '
                   'form a floral wreath or crown around the pet.'),
        'review': ('recognizable peonies and one to three restrained butterflies; no floral '
                   'wreath, and no motif obscuring the pet'),
    },
    'lotus': {
        'label': 'Lotus & Butterfly Garden',
        'korean': '연꽃과 나비',
        'meaning': 'peace, healing, and gentle renewal',
        'references': (
            'cat-17-lotus-butterflies.jpg', 'dog-22-lotus-butterflies.jpg',
            'cat-05-lotus-butterflies.jpg', 'dog-04-lotus-butterflies.jpg',
            'cat-06-lotus-butterflies.jpg', 'dog-05-lotus-butterflies.jpg',
        ),
        'recipe': ('Use a restrained grouping of lotus blossoms and broad leaves, a shallow '
                   'water rhythm near the lower edge, and one to three small butterflies. '
                   'Keep open hanji around the pet instead of filling the scene as a dense pond.'),
        'review': ('recognizable lotus blossoms and leaves, a shallow water rhythm, and one to '
                   'three restrained butterflies; no dense pond scenery'),
    },
    'pine': {
        'label': 'Pine & Magpie Garden',
        'korean': '소나무와 까치',
        'meaning': 'protection, steadfastness, and welcome news',
        'references': (
            'cat-18-pine-magpie.jpg', 'dog-23-pine-magpie.jpg',
            'cat-09-pine-magpie.jpg', 'dog-09-pine-magpie.jpg',
            'cat-10-pine-magpie.jpg', 'dog-10-pine-magpie.jpg',
        ),
        'recipe': ('Use one weathered, crooked pine structure and exactly one Korean magpie. '
                   'A single low fantastical rock may support the composition. Include no '
                   'butterflies, peonies, or lotus.'),
        'review': ('one weathered pine structure and exactly one magpie, with at most one low '
                   'rock; no butterflies, peonies, or lotus'),
    },
}
GARDEN_ANCHORS = {
    garden: tuple(ANCHOR_ROOT / name for name in recipe['references'])
    for garden, recipe in GARDENS.items()
}


def garden_anchors(garden):
    """Return the six curated runtime references for one garden."""
    try:
        return GARDEN_ANCHORS[garden]
    except KeyError:
        raise ValueError('Choose peony, lotus, or pine.') from None


def generation_inputs(source, style, identity='', feedback=''):
    anchors = garden_anchors(style)
    source = Path(source).expanduser().resolve()
    references = [source, *anchors]
    for path in references:
        if not path.is_file():
            raise ValueError(f'Generation reference is missing: {path.name}. Restore it before generating.')
    garden = GARDENS[style]
    role_map = '\n'.join(
        f'Image {index}: {role}. Use only this role; never copy the reference pet.'
        for index, role in enumerate(REFERENCE_ROLES, start=2)
    )
    prompt = f'''Create a wholly new 4:5 Korean minhwa pet portrait. Art direction: {WORKFLOW_VERSION}.

REFERENCE AUTHORITY
The seven attached images have distinct roles. Image 1 is the CUSTOMER IDENTITY AND POSE AUTHORITY. Images 2-7 are ART REFERENCES only, never pet identity references. Inspect every reference visually.
{role_map}

REFERENCE SET POSE BALANCE
Images 2-3 are direct-to-viewer calibration plates: the fictional pet faces forward while the fauna remains environmental. Images 4-7 preserve varied, natural three-quarter, standing, reclining, and motif-interaction compositions. This balance prevents any single reference-pose pattern from becoming a default. It never overrides image 1.

PORTRAIT PRIORITY
Preserve the exact observable pet from image 1: face geometry, eye spacing and visible eye color, ear carriage, muzzle ratio, age cues, coat colors and patch locations, body proportions, tail, coat direction, characteristic expression, and the photographed pose. Preserve the source head angle and gaze. Do not force the pet to look at a butterfly, magpie, flower, or any other motif. Build the garden around the pet instead of changing the pet to match a reference composition.
Do not borrow breed, anatomy, markings, color, facial features, or posture from images 2-7. Do not invent hidden markings or body parts. If the photograph is cropped, keep a compatible portrait crop rather than fabricating a full body. Discard the source room and camera lighting. This is fresh synthesis, not a filtered photograph, pixel edit, or tracing.

GARDEN RECIPE
Selected garden: {garden['label']} / {garden['korean']}. Symbolic intention: {garden['meaning']}.
{garden['recipe']}
Keep every motif subordinate in scale, contrast, detail, and placement. Do not overlap the eyes, muzzle, ears, defining markings, paws, or tail. The pet must be the first focal point at thumbnail size. Reserve 28-35% calm open paper and a blank inscription area for verified post-production calligraphy.

TRADITIONAL PAINTING LANGUAGE
Use shallow stacked symbolic space, warm mulberry hanji, matte ink and layered mineral or plant-like pigment, restrained barim, fine organic contours, and affectionate irregularity. Unify the pet and garden in the same painted material language. The face and eyes may carry the highest descriptive detail, but avoid photographic fur, glossy eyes, lens blur, cinematic lighting, pasted cutouts, airbrushed realism, anime, or generic watercolor clip art.

OUTPUT SAFEGUARDS
Exactly one pet. Keep the recognizable silhouette and all intentionally visible ears, paws, and tail inside safe margins. Do not copy a reference composition exactly or combine unrelated motifs. No hanbok, crowns, palace, temple, generic pan-Asian ornament, letters, names, signatures, seals, watermarks, promotional borders, or frame. The website adds verified text and seal later.
'''
    if identity:
        prompt += ('\nObserved identity notes to verify against image 1. The photograph always '
                   'takes precedence; never invent uncertain or unseen details:\n' + identity + '\n')
    if feedback:
        prompt += '\nCorrection priority for this fresh painting: ' + feedback + '\n'
    return {
        'prompt': prompt,
        'referenced_image_paths': [str(path) for path in references],
        'transparent_background': False,
        'reference_hashes': [hashlib.sha256(path.read_bytes()).hexdigest() for path in references],
        'reference_files': [path.name for path in anchors],
        'reference_roles': list(REFERENCE_ROLES),
        'style': style,
        'garden_label': garden['label'],
        'garden_review': garden['review'],
        'workflow_version': WORKFLOW_VERSION,
    }


def main():
    parser = argparse.ArgumentParser(description='Prepare one identity photo and six curated garden references; no model API calls.')
    parser.add_argument('--source', type=Path, required=True, help='Pet identity photo (PNG, JPEG, or WebP).')
    parser.add_argument('--style', choices=tuple(GARDENS), default='peony', help='Garden recipe (legacy API name).')
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
    print('In Codex, inspect all seven images and pass this JSON to the built-in image generation tool.')


if __name__ == '__main__':
    main()
