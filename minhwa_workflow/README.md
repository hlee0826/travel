# Minhwa pet-art workflow

Create a new Korean minhwa-inspired painting using one pet photo for identity and four supplied paintings for style and composition. This folder is self-contained and can be copied into another project.

Version: `minhwa-anchors-v3`. The prompt matches the tested local studio workflow. The website imports this module so both use the same art direction.

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

Choose `peony` or `lotus`. Missing image files fail preparation. Existing output files are never overwritten; choose a new run folder for each revision. The script resolves reference paths on the current computer, so regenerate the JSON after moving the folder or changing computers.

The output JSON contains the built-in image tool's exact `prompt`, `referenced_image_paths`, and `transparent_background` arguments. Its attachment order is significant:

| Image | File | Role |
| --- | --- | --- |
| 1 | Your pet photo | Identity only: ears, proportions, age, eyes, coat patches |
| 2 | `style-anchors/peony-tuxedo-cat.png` | Peony framing, pigment, botanical drawing |
| 3 | `style-anchors/peony-tabby-cat.png` | Peony framing, negative space, pet scale |
| 4 | `style-anchors/lotus-corgi.png` | Lotus composition and traditional painted forms |
| 5 | `style-anchors/bamboo-white-dog.png` | Spacious botanical framing; ignore promotional margins |

Peony requests emphasize images 2–3; lotus requests emphasize image 4. All four remain attached as style anchors. The reference pets never supply the new pet's identity.

## Generate in Codex

Paste this instruction into Codex after preparing the request, substituting the actual JSON path:

> Read `minhwa_workflow/runs/portrait-1/generation-inputs.json`. Inspect all five images in its attachment order. Use the built-in image generation tool with the JSON's exact prompt, referenced_image_paths, and transparent_background arguments. Attach all five actual files, not descriptions. Create one new painting and save the tool's output to `minhwa_workflow/runs/portrait-1/artwork.png`. Do not use an external model API or local filters. Review the result against the checklist in `minhwa_workflow/README.md`; revise if necessary. Preserve the original photo and anchors.

The photo is an identity reference, never a pixel base, tracing, background, pose lock, or image to filter. Generate a fresh pose with the head, muzzle, and eyes directed toward the same nearby butterfly. Use grouped fur colors, ink contours, restrained pigment shading, and traditional botanical composition. Do not feed earlier generated portraits back as references.

If the built-in tool is unavailable, stop and report that limitation. Do not silently switch to a paid API or attach a demo as if it were generated from the pet photo.

## Review before accepting

1. The pet remains recognizable: ear silhouette, muzzle proportions, age, eye color, coat patches, and body proportions come from image 1.
2. The painting has a fresh composition and pose, without the photo's setting or camera lighting.
3. Pet and plants share a traditional painted appearance. Reject photographic cutouts, photo texture beneath a paper filter, excessive fur detail, or modern cartoon rendering.
4. The head, muzzle, and visible pupils aim toward one butterfly in a believable sightline.
5. Exactly one pet, coherent anatomy, and safe margins around ears and paws. Do not invent unseen identifying markings.
6. No copied reference text, names, seals, signatures, promotional borders, or watermarks. Add optional customer text separately after generation.

Keep the input JSON alongside each accepted result. Record the workflow version and the four anchor filenames when integrating into an application. Visual review is manual; passing tests does not establish image quality or print readiness.

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

Tests exercise both compositions, ordered readable references, missing inputs, invalid style selection, portable command execution, and refusal to overwrite existing output. No generation call is made during tests.

## ComfyUI status

ComfyUI is the selected future production engine, but this working version uses Codex's built-in image tool. There is no executable ComfyUI graph, installed checkpoint, adapter, or model download in this folder. A production implementation must separately condition identity and style, synthesize a fresh image, and pass the review criteria above. A low-change image-to-image filter does not meet the requirement.

## Reference provenance and local data

The four PNGs are unchanged user-supplied style references. Their depicted pets, lettering, and artist marks are not output assets to reproduce. No ownership or redistribution license for the third-party reference art is asserted by this repository.

`runs/` is ignored by Git. Keep uploaded pet photos and generated request files there or outside the repository; the prepared JSON contains absolute local paths. No user pet photos, generated portraits, API credentials, browser cookies, or order records are bundled here.
