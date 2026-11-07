# Minhwa pose reference workflow

Version: `minhwa-poses-v5`. The local and hosted applications share this eight-bucket workflow. The uploaded photo supplies identity; one or two selected paintings supply style and compatible composition. Only the selected set is attached to generation and artwork review.

## Photo assessment

The existing photo-review call returns only `usable`, `bucket`, and `reason`. It checks for one identifiable cat or dog with a clear visible face and chooses a bucket. It does not produce an identity narrative, anatomy report, confidence score, or separate angle fields.

| Bucket | Composition |
| --- | --- |
| standing_front | Standing, looking forward |
| standing_profile | Standing, watching a butterfly |
| sitting_front | Sitting, looking forward |
| sitting_profile | Sitting, watching a butterfly |
| reclining_front | Reclining, looking forward |
| reclining_profile | Reclining, watching a butterfly |
| portrait_front | Head/chest portrait, looking forward |
| portrait_profile | Head/chest portrait, watching a butterfly |

Head/chest crops or insufficient body evidence use portrait buckets. Front/profile follows the face, not the torso. Three-quarter faces use the closest compatible view without a large head turn. Unusable or unmatchable photos return a null bucket and stop before painting. The reason is empty on success and a short explanation on failure.

## Add references later

All eight entries in each garden are initially **pending** in `reference-catalog.json`. No legacy anchor is silently substituted. The old files remain on disk for historical records.

1. Put one or two curated PNG, JPEG, or WebP images under `style-anchors/`, for example `style-anchors/peony/standing_front/anchor-1.png`.
2. Inspect them for the intended pose, consistent minhwa painting style, botanical setting, and clean framing. Use references with appropriate permissions. Avoid advertisement margins and text.
3. Set the matching garden/bucket entry to `ready`, with paths relative to `style-anchors/`:

```json
{
  "status": "ready",
  "references": ["peony/standing_front/anchor-1.png"]
}
```

4. Run the tests and a prepared request for that bucket, then validate generated results before deploying the updated catalog and files.

Absolute paths, parent traversal, duplicate files, and more than two references are rejected. Missing files stop generation. Pending branches display `composition_unavailable`; they do not reject the photo or issue an image-generation request. Retry becomes available once the selected branch is ready. Earlier attempts retain their spending reservation and count toward the existing limits.

Keep palette, brushwork, paper, plant drawing, and detail level consistent across sets. Reference animals must not supply identity or markings. No left/right sub-buckets are required.

## Prepare a standalone request

Python 3.10 or newer is sufficient for this portable module; no model API call is made. Inspect the photo and explicitly choose a bucket first.

```sh
python3 minhwa_workflow/workflow.py \
  --source /absolute/path/to/pet.png \
  --style peony \
  --bucket standing_front \
  --output /absolute/path/to/new-inputs.json
```

The output contains the exact prompt, ordered `referenced_image_paths`, `transparent_background`, selected bucket and garden, workflow/catalog versions, relative reference filenames, composition instructions, and file hashes. Existing output files are never overwritten.

When using Codex's built-in image tool, inspect every listed image and pass only the prompt, referenced_image_paths, and transparent_background arguments. Attach all listed files in order. Do not substitute descriptions or use previous portraits. Review the painting against its source, selected references, and saved composition. No external API call is authorized by this manual preparation.

## Local manual studio

New uploads in manual mode wait at `awaiting_assessment`. Read the request, inspect the photo, and record its bucket:

```sh
.venv/bin/python studio.py prepare JOB_ID --bucket portrait_front
```

If references are ready, the job becomes `awaiting_artwork` and its updated `request.txt` describes generation and review. If references are missing, it becomes `composition_unavailable`; rerun preparation after supplying the references. Attach reviewed artwork with `studio.py complete JOB_ID /absolute/path/artwork.png`. The server verifies the prepared reference hashes before accepting new-workflow manual results.

## Generation and review

Front buckets require forward gaze, with butterflies optional as decoration. Profile buckets require a plausible butterfly sightline. Portrait buckets permit intentional chest framing without inventing a lower body. All branches preserve likeness and visible markings, use a fresh painted garden, and avoid photo texture, copied text, signatures, or frames.

Artwork review receives the original photo, generated painting, selected references, and the same saved composition instructions. A fresh scene does not require a changed posture. All nine quality checks must pass for automatic release; the customer still approves likeness.

Each attempt saves its selection. Hosted stages restore it without rereading the catalog for a new selection; changed source or reference bytes block continuation. Already approved artwork and orders remain unchanged. Old hosted attempts lacking a saved selection stop for studio reconciliation rather than mixing old and new instructions; a new attempt uses v5. Existing manual v4 handoffs can be completed as recorded; their next preparation uses an explicit v5 bucket.

## Tests

```sh
python3 -m unittest discover -s minhwa_workflow -p 'test_*.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Tests use temporary assets and mocked providers, never mark real pending entries ready, and do not establish visual quality or measured API savings. Validate real branch references with consented sample photos before enabling production use. Keep uploaded photos and generated inputs outside the tracked reference directories; `runs/` is ignored.
