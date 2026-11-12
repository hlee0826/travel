# Minhwa pet-art workflow

Version: `minhwa-gardens-v7`. The local and hosted studios use the same two-stage art direction.

## Why two generation stages

The customer photograph first produces an undecorated identity study on plain warm hanji. That study must pass likeness, pose/crop, anatomy, matte-pigment, no-shine, and hanji-integration checks, then receive customer approval.

The approved study and five curated references from the selected garden then guide a separate whole-canvas generation. The final stage repaints the pet and garden together; it must never paste, mask, composite, or preserve pixels from the identity study. The original photograph remains the final likeness comparison but is not attached to the final image-generation call.

The 41-image experimental source library remains in `reference_library_v2/`. Only five references per garden—15 total—are active for final synthesis. The full library is never attached to a customer request.

## Stage 1 — identity study

```sh
python3 minhwa_workflow/workflow.py \
  --stage identity \
  --source /absolute/path/to/pet.png \
  --output minhwa_workflow/runs/portrait-1/identity-inputs.json
```

Attachment order:

| Image | Role |
| --- | --- |
| 1 | Customer identity, visible pose, head angle, gaze, crop, markings, and proportions |

Generate one undecorated study. Reject it if it contains a garden, invented hidden anatomy, glossy coat highlights, photographic microtexture, camera lighting, or a hard cutout edge. Record customer approval before continuing.

## Stage 2 — integrated garden

```sh
python3 minhwa_workflow/workflow.py \
  --stage integrated \
  --source /absolute/path/to/approved-identity-study.png \
  --style peony \
  --output minhwa_workflow/runs/portrait-1/integrated-inputs.json
```

Choose `peony`, `lotus`, or `pine`. Attachment order:

| Image | Role |
| --- | --- |
| 1 | Approved painted identity study: identity, posture, expression, markings, and crop |
| 2 | Overall garden composition and pet-to-motif scale |
| 3 | Quiet space and asymmetric edge framing |
| 4 | Traditional botanical or arboreal motif drawing |
| 5 | Hanji, matte pigment, ink contour, and material unity |
| 6 | Mineral palette, barim, and shallow symbolic space |

The final prompt fixes pet scale by crop type, 28–35% quiet paper, subordinate motif ranges, a returning visual path, shared edge/light/material language, and whole-canvas synthesis.

## Acceptance gates

Identity study:

1. Same individual pet and observable markings.
2. Original posture, head angle, gaze, and crop preserved.
3. No invented hidden anatomy.
4. Entire pet is visibly painted in matte pigment on hanji.
5. No photographic shine, microtexture, lighting, or cutout edge.
6. No motifs, props, text, border, or frame.

Final artwork:

1. Identity, markings, anatomy, and source pose still pass.
2. Pet and garden share paper grain, pigment absorption, contour, barim, palette, and diffuse light.
3. Pet scale, motif scale, and quiet-space distribution meet the composition contract.
4. The visual path returns to the pet and the piece reads as one balanced, wall-worthy artwork.
5. The selected garden is coherent; motifs remain subordinate and do not cover recognition anchors.
6. No photographic shine, pasted-study edge, unrelated motifs, generated text, seal, border, or watermark.

Every automated boolean gate must pass. Final release still requires customer approval and the project’s 82/100 QA minimum.

## Application integration

```python
from minhwa_workflow.workflow import identity_inputs, generation_inputs

identity = identity_inputs('/absolute/path/to/normalized-pet.png')
# Generate, review, and obtain customer approval.
final = generation_inputs('/absolute/path/to/approved-identity-study.png', 'peony')
```

The consuming application must checkpoint every paid call, store the approved identity study privately, preserve its hash, and reuse it for final-art retries. An identity rejection returns to stage 1; a final-art rejection stays in stage 2.

## Tests and data handling

```sh
python3 -m unittest discover -s minhwa_workflow -p 'test_*.py' -v
```

`runs/` is ignored by Git. No customer photos, generated portraits, API credentials, cookies, or order records belong in the repository. Missing or changed references fail preparation; existing JSON outputs are never overwritten.
