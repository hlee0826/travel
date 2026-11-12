# Minhwa pet-art workflow

Create a new Korean minhwa-inspired painting using one customer photo for identity and pose plus six curated art references from the selected garden. This folder is self-contained and can be copied into another project.

Version: `minhwa-gardens-v6`. The prompt matches the local and hosted studio workflow. The website imports this module so both use the same art direction.

## Experimental Integrated Garden Reference Library

`reference_library_v2/` is the 41-image experimental source library distributed
across peony-and-butterfly, lotus-and-butterfly, plum-blossom-and-butterfly, and
pine-and-magpie gardens. Exactly 18 references are active at runtime: six for
each customer-facing garden, and only one six-image set is attached to a given
generation. Superseded local copies may remain in `garden-anchors/`, but the
workflow does not attach them. Active references control material, motif,
palette, composition and symbolic space; they never replace the customer
photo's individual identity or pose.

Every runtime set now has a deliberate 2+4 pose balance: one cat and one dog
face directly toward the viewer while four other plates preserve natural
three-quarter, standing, reclining, and fauna-interaction compositions. The
forward-facing plates prevent the library from teaching a universal sideways
gaze; they do not ask the generated customer pet to copy that pose.

## Requirements

- Python 3.10 or newer. Request preparation and tests use only the standard library; there are no packages to install.
- Codex with its built-in image generation tool available for the actual generation step. No API key is required. This script prepares inputs; it does not invoke a model automatically.
- Your pet photo in PNG, JPEG, or WebP format. Convert HEIC before standalone use; the local studio already normalizes HEIC uploads.

## Prepare a request

From the repository root:

```sh
python3 minhwa_workflow/workflow.py \
  --source /absolute/path/to/pet.png \
  --style peony \
  --output minhwa_workflow/runs/portrait-1/generation-inputs.json
```

Choose `peony`, `lotus`, or `pine`. Missing image files fail preparation. Existing output files are never overwritten; choose a new run folder for each revision. The script resolves reference paths on the current computer, so regenerate the JSON after moving the folder or changing computers.

The output JSON includes `reference_hashes` for integrity checking plus the built-in image tool's `prompt`, `referenced_image_paths`, and `transparent_background` arguments. Its attachment order is significant:

| Image | File | Role |
| --- | --- | --- |
| 1 | Your pet photo | Individual identity, visible pose, head angle, gaze, crop, markings and proportions |
| 2 | Selected garden reference | Overall composition and pet-to-motif scale |
| 3 | Selected garden reference | Quiet space and asymmetric edge framing |
| 4 | Selected garden reference | Traditional motif drawing |
| 5 | Selected garden reference | Hanji, matte pigment, fine ink contour and material unity |
| 6 | Selected garden reference | Mineral palette and restrained barim |
| 7 | Selected garden reference | Shallow symbolic space and visual rhythm |

Each garden has its own six-image runtime set in `garden-anchors/`. Only those six are attached for a request; the full experimental library is not sent. Reference pets never supply the customer pet's identity, anatomy, markings, or posture.

Images 2 and 3 are the direct-to-viewer calibration pair. Images 4 through 7
provide varied natural interaction and pose structures. Image 1 remains the
only authority for the customer's actual posture, head angle, and gaze.

## Generate in Codex

Paste this instruction into Codex after preparing the request, substituting the actual JSON path:

> Read `minhwa_workflow/runs/portrait-1/generation-inputs.json`. Inspect all seven images in their attachment order. Use the built-in image generation tool with the JSON's exact prompt, referenced_image_paths, and transparent_background arguments. Attach all seven actual files, not descriptions. Create one new painting and save the tool's output to `minhwa_workflow/runs/portrait-1/artwork.png`. Do not use an external model API or local filters. Review the result against the checklist in `minhwa_workflow/README.md`; revise if necessary. Preserve the original photo and references.

The photo is the identity and pose authority, never a pixel base, tracing, background, or image to filter. Preserve its visible posture, head angle, gaze and crop. Compose the selected garden around the pet; never force a butterfly or magpie sightline. Use grouped fur colors, ink contours, restrained pigment shading, and traditional motif structure. Do not feed earlier generated portraits back as references.

If the built-in tool is unavailable, stop and report that limitation. Do not silently switch to a paid API or attach a demo as if it were generated from the pet photo.

## Review before accepting

1. The pet remains recognizable: ear silhouette, muzzle proportions, age, eye color, coat patches, and body proportions come from image 1.
2. The painting has a fresh garden while preserving the photo's visible pose, head angle, gaze and crop; it does not reproduce the source setting or camera lighting.
3. Pet and plants share a traditional painted appearance. Reject photographic cutouts, photo texture beneath a paper filter, excessive fur detail, or modern cartoon rendering.
4. The selected garden is coherent: peony or lotus uses restrained butterflies; pine uses exactly one magpie and no unrelated flower garden.
5. The pet is the first focal point and motifs remain subordinate without covering recognition anchors.
6. Exactly one pet, coherent anatomy, and safe margins around ears, paws and tail. Do not invent unseen identifying markings.
7. No copied reference text, names, seals, signatures, promotional borders, or watermarks. Add verified customer text separately after generation.

Keep the input JSON alongside each accepted result. Record the workflow version and six selected filenames when integrating into an application. Visual review is manual; passing tests does not establish image quality or print readiness.

## Application integration

```python
from minhwa_workflow.workflow import generation_inputs, WORKFLOW_VERSION

inputs = generation_inputs('/absolute/path/to/normalized-pet.png', 'peony')
# Save inputs in the private job folder, then hand them to Codex's image tool.
```

The consuming app must validate and normalize uploads, restrict access to private job files, and require approval of a generated candidate before ordering. The local Minhwa studio handles these steps and attaches tool outputs through `studio.py complete JOB_ID /absolute/path/artwork.png`. That website and its session/order data are separate from this portable folder.

## Tests

```sh
python3 -m unittest discover -s minhwa_workflow -p 'test_*.py' -v
```

Tests exercise all three gardens, ordered readable references, missing inputs, invalid garden selection, portable command execution, and refusal to overwrite existing output. No generation call is made during tests.

## ComfyUI status

ComfyUI was an earlier proposed engine. The website now uses OpenAI directly; this standalone handoff uses Codex's built-in image tool. There is no executable ComfyUI graph, installed checkpoint, adapter, or model download in this folder. A production implementation must separately condition identity and style, synthesize a fresh image, and pass the review criteria above. A low-change image-to-image filter does not meet the requirement.

## Reference provenance and local data

The runtime garden references are a curated subset of the experimental reference library. Their depicted fictional pets are not output identities to reproduce. The prompt assigns each reference one limited art-direction role.

`runs/` is ignored by Git. Keep uploaded pet photos and generated request files there or outside the repository; the prepared JSON contains absolute local paths. No user pet photos, generated portraits, API credentials, browser cookies, or order records are bundled here.
