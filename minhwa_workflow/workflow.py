"""Prepare the approved two-stage identity-to-garden minhwa workflow."""
import argparse
import hashlib
import json
from pathlib import Path


WORKFLOW_VERSION = 'minhwa-gardens-v8'
ANCHOR_ROOT = Path(__file__).resolve().parent / 'garden-anchors'
REFERENCE_ROLES = (
    'overall garden composition and pet-to-motif scale',
    'quiet space and asymmetric edge framing',
    'traditional botanical or arboreal motif drawing',
    'hanji, matte pigment, fine ink contour, and unified pet-and-garden treatment',
    'mineral-pigment palette, restrained barim, and shallow symbolic space',
)
GARDENS = {
    'peony': {
        'label': 'Peony & Butterfly Garden',
        'meaning': 'flourishing affection, beauty, and celebration',
        'references': (
            'cat-16-peony-butterflies.jpg', 'cat-02-peony-butterflies.jpg',
            'dog-02-peony-butterflies.jpg', 'cat-03-peony-butterflies.jpg',
            'dog-03-peony-butterflies.jpg',
        ),
        'recipe': ('Use one restrained peony branch or flower mass entering from an edge and '
                   'one to three small butterflies as subordinate movement elements. Do not '
                   'form a floral wreath or crown around the pet.'),
        'review': ('recognizable peonies and one to three restrained butterflies; no floral '
                   'wreath, and no motif obscuring the pet'),
        'composition': ('For a bust or close three-quarter crop, keep the pet at 58-66% of canvas '
                        'height; for a visible full body, 50-58%. The peony structure may occupy '
                        '15-24% of the picture while remaining subordinate to the face.'),
    },
    'lotus': {
        'label': 'Lotus & Butterfly Garden',
        'meaning': 'peace, healing, and gentle renewal',
        'references': (
            'cat-17-lotus-butterflies.jpg', 'cat-05-lotus-butterflies.jpg',
            'dog-04-lotus-butterflies.jpg', 'cat-06-lotus-butterflies.jpg',
            'dog-05-lotus-butterflies.jpg',
        ),
        'recipe': ('Use a restrained grouping of lotus blossoms and broad leaves, a shallow '
                   'water rhythm near the lower edge, and one to three small butterflies. '
                   'Keep open hanji around the pet instead of filling the scene as a dense pond.'),
        'review': ('recognizable lotus blossoms and leaves, a shallow water rhythm, and one to '
                   'three restrained butterflies; no dense pond scenery'),
        'composition': ('For a bust or close three-quarter crop, keep the pet at 56-64% of canvas '
                        'height; for a visible full body, 50-58%. Lotus leaves and blossoms may '
                        'occupy 16-25% of the picture while preserving calm open paper.'),
    },
    'pine': {
        'label': 'Pine & Magpie Garden',
        'meaning': 'protection, steadfastness, and welcome news',
        'references': (
            'cat-18-pine-magpie.jpg', 'cat-09-pine-magpie.jpg',
            'dog-09-pine-magpie.jpg', 'cat-10-pine-magpie.jpg',
            'dog-10-pine-magpie.jpg',
        ),
        'recipe': ('Use one weathered, crooked pine structure and exactly one Korean magpie. '
                   'A single low fantastical rock may support the composition. Include no '
                   'butterflies, peonies, or lotus. Treat the pine as a mature landscape anchor, '
                   'not a decorative branch behind an oversized pet.'),
        'review': ('one weathered pine structure and exactly one magpie, with at most one low '
                   'rock; no butterflies, peonies, or lotus'),
        'composition': ('PINE-SPECIFIC SCALE: make the pet visibly smaller than the mature tree. '
                        'For a bust, reclining, or close three-quarter crop, the pet bounding box '
                        'must occupy only 46-54% of canvas height and no more than 44% of canvas '
                        'width; for a visible full body, 42-50% of canvas height. The pine trunk '
                        'and canopy together must read at least 1.35 times the pet height, span '
                        '55-75% of the canvas width, and form 28-38% of the total visual mass. '
                        'Keep the pet in the lower middle with open paper around its head. Minhwa '
                        'may use symbolic scale, but the tree must unmistakably read as the larger '
                        'environmental structure rather than a pet-sized prop.'),
    },
}
GARDEN_ANCHORS = {
    garden: tuple(ANCHOR_ROOT / name for name in recipe['references'])
    for garden, recipe in GARDENS.items()
}


def garden_anchors(garden):
    """Return the five curated final-synthesis references for one garden."""
    try:
        return GARDEN_ANCHORS[garden]
    except KeyError:
        raise ValueError('Choose peony, lotus, or pine.') from None


def _checked(paths):
    for path in paths:
        if not path.is_file():
            raise ValueError(f'Generation reference is missing: {path.name}. Restore it before generating.')


def identity_inputs(source, identity='', feedback=''):
    """Prepare a plain-hanji identity study from the customer photograph."""
    source = Path(source).expanduser().resolve()
    _checked((source,))
    prompt = f'''Create an undecorated 4:5 Korean minhwa identity study of the one pet in the attached customer photograph. Art direction: {WORKFLOW_VERSION}.

IDENTITY AUTHORITY
The photograph is the sole authority for this individual pet. Preserve exact observable face geometry, eye spacing and visible eye color, ear carriage, muzzle ratio, age cues, coat colors and patch locations, body proportions, coat direction, characteristic expression, photographed posture, head angle, gaze, and crop. Do not guess breed. Do not invent hidden markings, limbs, torso, paws, or tail. If the photograph is cropped, preserve a compatible portrait crop instead of fabricating a full body.

MATERIAL TRANSLATION
Repaint the pet completely as Korean fine-brush painting on plain warm mulberry hanji: matte ink, translucent layered mineral or plant-like pigment, restrained barim, tapered organic contours, simplified grouped coat strokes, and diffuse paper-embedded light. Preserve recognition while removing photographic shine, specular coat highlights, lens blur, camera lighting, photographic microtexture, airbrushed volume, and hard cutout edges.

STUDY LIMITS
Exactly one pet on an undecorated warm hanji field. No garden, flowers, pine, magpie, butterfly, lotus, rock, water, room, furniture, props, text, calligraphy, seal, border, or frame. Leave calm paper around the visible silhouette. This is a fresh painting, not a filtered photograph, tracing, cutout, or collage.
'''
    if identity:
        prompt += ('\nObserved identity notes to verify against the photograph. The photograph always '
                   'takes precedence; never invent uncertain or unseen details:\n' + identity + '\n')
    if feedback:
        prompt += '\nCorrection priority for this identity study: ' + feedback + '\n'
    return {
        'prompt': prompt,
        'referenced_image_paths': [str(source)],
        'transparent_background': False,
        'reference_hashes': [hashlib.sha256(source.read_bytes()).hexdigest()],
        'workflow_version': WORKFLOW_VERSION,
        'stage': 'identity-study',
    }


def generation_inputs(identity_study, style, identity='', feedback=''):
    """Prepare whole-canvas synthesis from an approved study and five art references."""
    anchors = garden_anchors(style)
    identity_study = Path(identity_study).expanduser().resolve()
    references = [identity_study, *anchors]
    _checked(references)
    garden = GARDENS[style]
    role_map = '\n'.join(
        f'Image {index}: {role}. Use only this role; never copy the reference pet.'
        for index, role in enumerate(REFERENCE_ROLES, start=2)
    )
    prompt = f'''Create a wholly new, wall-worthy 4:5 Korean minhwa pet portrait by repainting the entire canvas as one coherent work. Art direction: {WORKFLOW_VERSION}.

REFERENCE AUTHORITY
The six attached images have distinct roles. Image 1 is the APPROVED PAINTED IDENTITY STUDY and the sole authority for the pet's identity, posture, expression, markings, and crop. Images 2-6 are ART REFERENCES only, never pet identity references. Inspect every reference visually.
{role_map}

PORTRAIT PRIORITY
Preserve the exact approved pet from image 1, including its painted face geometry, eye spacing and color, ear carriage, muzzle ratio, age cues, markings, body proportions, coat direction, expression, pose, head angle, gaze, and crop. Do not force the pet to look at a butterfly, magpie, flower, or any motif. Build the garden around the approved posture. Do not borrow breed, anatomy, markings, color, facial features, or posture from images 2-6. Do not invent hidden anatomy.

WHOLE-CANVAS SYNTHESIS — NO LAYER COMPOSITING
Repaint the pet, hanji field, ground, and every motif together from scratch in one generation. Do not paste, preserve, mask, inpaint around, or reuse pixels from image 1. The approved study governs identity and painted material; it is not a foreground layer. Give pet and garden the same paper grain, pigment absorption, contour character, barim softness, palette logic, and diffuse light so every edge belongs to one painting.

GARDEN RECIPE
Selected garden: {garden['label']}. Symbolic intention: {garden['meaning']}.
{garden['recipe']}
Keep every motif subordinate in scale, contrast, detail, and placement. Do not overlap the eyes, muzzle, ears, defining markings, paws, or tail. The pet must be the first focal point at thumbnail size. Reserve 28-35% calm open paper and a blank inscription area for verified post-production calligraphy.

COMPOSITION CONTRACT
Preserve image 1's approved posture, head angle, gaze, expression, markings, and visible anatomy while changing only its frame share when the selected garden requires it. {garden['composition']} Keep 28-35% quiet paper. A supporting rock or leaf mass occupies 6-10%, and each small bird or butterfly 3-5%. Place the pet near the lower center, at most 8% off-center, with open paper around the head. Build a soft triangular or S-shaped visual path from the eyes to the nearest motif, to a quieter counterweight, and back through the chest or silhouette. Judge scale relationally before adding detail: the pet, anchor motif, quiet paper, and fauna must feel intentionally proportioned as one painting. No motif may create a halo, crowd the face, or pull attention out of the frame.

TRADITIONAL PAINTING LANGUAGE
Use shallow stacked symbolic space, warm mulberry hanji, matte ink and layered mineral or plant-like pigment, restrained barim, fine organic contours, and affectionate irregularity. The face and eyes may carry the highest descriptive detail, but the pet must remain visibly painted. Avoid photographic fur, individual glossy hairs, glossy eyes, lens blur, cinematic lighting, pasted cutouts, airbrushed realism, anime, or generic watercolor clip art.

OUTPUT SAFEGUARDS
Exactly one pet. Keep the recognizable silhouette and all intentionally visible ears, paws, and tail inside safe margins. Do not copy a reference composition exactly or combine unrelated motifs. No hanbok, crowns, palace, temple, generic pan-Asian ornament, letters, names, signatures, seals, watermarks, promotional borders, or frame. The website adds verified text and seal later.
'''
    if identity:
        prompt += ('\nLocked identity notes used to audit the approved study. Image 1 remains the '
                   'visual authority; never invent uncertain or unseen details:\n' + identity + '\n')
    if feedback:
        prompt += '\nCorrection priority for this fresh whole-canvas painting: ' + feedback + '\n'
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
        'stage': 'integrated-artwork',
    }


def main():
    parser = argparse.ArgumentParser(description='Prepare an identity study or final synthesis; no model API calls.')
    parser.add_argument('--source', type=Path, required=True, help='Customer photo or approved identity study.')
    parser.add_argument('--style', choices=tuple(GARDENS), default='peony', help='Garden recipe.')
    parser.add_argument('--stage', choices=('identity', 'integrated'), default='identity')
    parser.add_argument('--output', type=Path, required=True, help='New JSON file; existing files are never overwritten.')
    args = parser.parse_args()
    try:
        inputs = identity_inputs(args.source) if args.stage == 'identity' else generation_inputs(args.source, args.style)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(inputs, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
    print(f'Prepared {args.output.resolve()}')
    print('In Codex, inspect every listed image and pass this JSON to the built-in image generation tool.')


if __name__ == '__main__':
    main()
