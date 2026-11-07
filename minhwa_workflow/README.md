# Minhwa pet-art workflow

Create a new Korean minhwa-inspired painting using a face photo and full-body photo of the same pet for identity, plus four supplied paintings for style and composition. This folder is self-contained and can be copied into another project.

Version: `minhwa-anchors-v5-two-photo-identity`. The prompt matches the tested local studio workflow. The website imports this module so both use the same art direction.

## Requirements

- Python 3.10 or newer. Request preparation and tests use only the standard library; there are no packages to install.
- Codex with its built-in image generation tool available for the actual generation step. No API key is required. This script prepares inputs; it does not invoke a model automatically.
- A face photo and a full-body photo of the same pet in PNG, JPEG, or WebP format. Convert HEIC before standalone use; the local studio already normalizes HEIC uploads.

## Prepare a request

From the repository root:

```sh
python3 minhwa_workflow/workflow.py \
  --source /absolute/path/to/pet-face.png \
  --body-source /absolute/path/to/pet-full-body.png \
  --style peony \
  --output minhwa_workflow/runs/portrait-1/generation-inputs.json
```

Choose `peony` or `lotus`. Missing image files fail preparation. Existing output files are never overwritten; choose a new run folder for each revision. The script resolves reference paths on the current computer, so regenerate the JSON after moving the folder or changing computers.

Both identity photos are required by the command-line workflow. The Python helper retains a single-photo compatibility path only so archived pre-v5 jobs can still be inspected; new integrations must always pass `body_source`.

The output JSON includes `reference_hashes` for integrity checking plus the built-in image tool's `prompt`, `referenced_image_paths`, and `transparent_background` arguments. Its attachment order is significant:

| Image | File | Role |
| --- | --- | --- |
| 1 | Your pet’s face photo | Face geometry, eyes, muzzle, ears, age cues and expression |
| 2 | Your pet’s full-body photo | Silhouette, proportions, coat, markings, paws and tail |
| 3 | `style-anchors/peony-tuxedo-cat.png` | Peony framing, pigment, botanical drawing |
| 4 | `style-anchors/peony-tabby-cat.png` | Peony framing, negative space, pet scale |
| 5 | `style-anchors/lotus-corgi.png` | Lotus composition and traditional painted forms |
| 6 | `style-anchors/bamboo-white-dog.png` | Spacious botanical framing; ignore promotional margins |

Peony requests emphasize images 3–4; lotus requests emphasize image 5. All four remain attached as style anchors. The reference pets never supply the new pet's identity.

## Generate in Codex

Paste this instruction into Codex after preparing the request, substituting the actual JSON path:

> Read `minhwa_workflow/runs/portrait-1/generation-inputs.json`. Inspect all six images in its attachment order. Use the built-in image generation tool with the JSON's exact prompt, referenced_image_paths, and transparent_background arguments. Attach all six actual files, not descriptions. Create one new painting and save the tool's output to `minhwa_workflow/runs/portrait-1/artwork.png`. Do not use an external model API or local filters. Review the result against the checklist in `minhwa_workflow/README.md`; revise if necessary. Preserve both original photos and all anchors.

The two photos are identity references, never a pixel base, tracing, background, pose lock, or images to filter. Preserve the pet’s observable expression; do not replace it with a generic happy or alert face to force a butterfly interaction. Use grouped fur colors, ink contours, restrained pigment shading, and traditional botanical composition. Do not feed earlier generated portraits back as references.

If the built-in tool is unavailable, stop and report that limitation. Do not silently switch to a paid API or attach a demo as if it were generated from the pet photo.

## Review before accepting

1. The pet remains recognizable: face geometry, eye spacing, muzzle, ears and expression come from image 1; coat patches, silhouette and body proportions come from image 2.
2. The painting has a fresh composition and pose, without the photo's setting or camera lighting.
3. Pet and plants share a traditional painted appearance. Reject photographic cutouts, photo texture beneath a paper filter, excessive fur detail, or modern cartoon rendering.
4. Any scene interaction follows a believable sightline without changing the pet’s distinctive expression.
5. Exactly one pet, coherent anatomy, and safe margins around ears and paws. Do not invent unseen identifying markings.
6. No copied reference text, names, seals, signatures, promotional borders, or watermarks. Add optional customer text separately after generation.

Keep the input JSON alongside each accepted result. Record the workflow version and the four anchor filenames when integrating into an application. Visual review is manual; passing tests does not establish image quality or print readiness.

## Application integration

```python
from minhwa_workflow.workflow import generation_inputs, WORKFLOW_VERSION

inputs = generation_inputs('/absolute/path/to/normalized-face.png', 'peony',
                           body_source='/absolute/path/to/normalized-full-body.png')
# Save inputs in the private job folder, then hand them to Codex's image tool.
```

The consuming app must validate and normalize uploads, restrict access to private job files, and require approval of a generated candidate before ordering. The local Minhwa studio handles these steps and attaches tool outputs through `studio.py complete JOB_ID /absolute/path/artwork.png`. That website and its session/order data are separate from this portable folder.

## Tests

```sh
python3 -m unittest discover -s minhwa_workflow -p 'test_*.py' -v
```

Tests exercise both compositions, ordered readable references, missing inputs, invalid style selection, portable command execution, and refusal to overwrite existing output. No generation call is made during tests.

## ComfyUI status

ComfyUI was an earlier proposed engine. The website now uses OpenAI directly; this standalone handoff uses Codex's built-in image tool. There is no executable ComfyUI graph, installed checkpoint, adapter, or model download in this folder. A production implementation must separately condition identity and style, synthesize a fresh image, and pass the review criteria above. A low-change image-to-image filter does not meet the requirement.

## Reference provenance and local data

The four PNGs are unchanged user-supplied style references. Their depicted pets, lettering, and artist marks are not output assets to reproduce. No ownership or redistribution license for the third-party reference art is asserted by this repository.

`runs/` is ignored by Git. Keep uploaded pet photos and generated request files there or outside the repository; the prepared JSON contains absolute local paths. No user pet photos, generated portraits, API credentials, browser cookies, or order records are bundled here.
