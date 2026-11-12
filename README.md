# Minhwa Studio

Main repository: [hlee0826/travel](https://github.com/hlee0826/travel). Live private preview: [minhwa.pinnedby.com](https://minhwa.pinnedby.com).

> Hosting: the Vercel + Supabase implementation and deployment instructions are in [docs/hosting.md](docs/hosting.md). The local studio below remains supported.

# Local development

A functioning local pet-art studio: upload a cat or dog photo, generate a new minhwa-inspired painting, review it, choose a keepsake, and download the approved artwork. Checkout and fulfillment remain simulated. The server binds only to this computer.

## Start

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python server.py
```

Open http://127.0.0.1:4187. No frontend build is required. Configuration is read at startup from private `.env.local`; environment variables override it. Copy `.env.example` for a new installation. Never put credentials in browser code or job records. Keep `.env.local` owner-readable only.

API mode requires `MINHWA_IMAGE_PROVIDER=openai`, `OPENAI_API_KEY`, Images Request and Responses Write permissions. The configured image model is `gpt-image-2.6-sunburst`; photo/artwork checks use `gpt-5-mini`. Requests use API credits. `MINHWA_IMAGE_PROVIDER=manual` retains the Codex handoff. See [API setup](docs/openai-api-setup.md).

## Working flow

1. Upload JPEG, PNG, WebP or HEIC, up to 20 MB / 40 megapixels, at least 600 pixels on each edge. Consent is required. Files are decoded, orientation-corrected, normalized and stripped of metadata.
2. A photo check requires one identifiable cat or dog with clear facial features. Rejected photos never reach the image endpoint.
3. The durable queue creates a 2432 × 3040 undecorated identity study from the photo alone. Automated review checks likeness, markings, pose, crop, invented anatomy, matte pigment, photographic shine, hanji integration and absence of decoration.
4. The customer approves that identity study before the garden stage can start.
5. A separate image call uses the approved painted study plus five selected garden references. It repaints the full canvas from scratch—never layer-compositing the study—with explicit pet scale, motif scale, quiet-space and returning-visual-path contracts.
6. Final automated review independently gates identity, anatomy, pose, selected-garden evidence, material unity, painted pet treatment, photographic shine, shared edges and light, pet/motif scale, quiet space, visual path, safe margins and overall wall-art harmony. Every boolean must pass before customer review.
7. Choose digital, print or natural-oak framed print. Physical sizes are 5 × 7 inches for your desk and 12 × 16 inches for your wall. Place a clearly labeled test order; no payment or supplier is contacted.
8. PNG/JPEG downloads use the saved approved master, including the optional name. The preview watermark is separate. A 12 × 16 sheet centers the complete 12 × 15 painting with half-inch top/bottom borders; it never crops the artwork.

## Flagged artwork review

Passing artwork needs no manual release. The studio CLI below handles flagged results. Automatic releases are recorded with reviewer `automated`; owner approval remains required before checkout.

```sh
.venv/bin/python studio.py pending
.venv/bin/python studio.py review JOB_ID CANDIDATE_ID --decision approve --note 'Compared source, references and artwork.'
.venv/bin/python studio.py review JOB_ID CANDIDATE_ID --decision reject --note 'Describe the visible issue.'
.venv/bin/python studio.py metrics
```

Inspect the source, all anchors and candidate before approval. Automated failure requires an explicit `--override` with a note; do not override a likeness problem merely to finish a job. `--reviewer codex-qa` records agent visual review honestly rather than claiming human approval. Owner acceptance is a separate check.

Timeouts and interrupted calls become `uncertain`. Check provider usage and saved attempt files before `studio.py reconcile JOB_ID --note 'What was verified'`. This enables a manual retry; it does not refund or erase the prior reservation. Requests are never automatically retried.

Manual mode still supports `studio.py complete JOB_ID /absolute/path/artwork.png` and `studio.py fail JOB_ID 'Explanation'`. The portable [workflow](minhwa_workflow/README.md) supplies its exact prompt and reference order.

## Art direction and saved files

`minhwa_workflow/workflow.py` is the authoritative `minhwa-gardens-v7` brief. Stage 1 uses only the customer photo to make an undecorated identity study. After approval, stage 2 uses that painted study plus five curated references for the selected peony, lotus, or pine garden. Inputs are normalized/downscaled for transmission, with hashes recorded. Missing or changed references block generation.

The pet and garden must share a traditional painted language, but motifs are composed around the photographed posture rather than forcing a butterfly or magpie sightline. No source-room background, photographic cutout, copied reference identity, unrelated motif accumulation, text, seal or signature. Optional names are rendered once into the master with bundled OFL-licensed Noto Serif KR. Likeness is reviewed, not mathematically guaranteed.

`.studio/jobs/JOB_ID/` retains the normalized source, attempts, prompts, reference hashes, provider metadata, review findings and approved artifacts. Pending/rejected artwork and raw masters are not public static files. Session ownership restricts media, orders and downloads. Existing approved orders keep immutable snapshots.

## Reliability and limits

- One process owns the worker. Atomic file writes and a cross-process storage lock coordinate the server and studio CLI. Queued jobs survive restarts; in-flight work is held for reconciliation rather than repeated.
- Duplicate upload and checkout submissions are idempotent. Refreshing or changing pages does not trigger generation.
- Maximum three attempts per portrait, three per identical photo per day, six per session per day, and two accepted paintings per portrait.
- Each attempt reserves $6 against a default $15 rolling 24-hour admission allowance (`MINHWA_DAILY_BUDGET_CENTS`) because a new portrait normally uses two image generations. Failed/uncertain attempts retain their reservation. This is a conservative request allowance, **not a guaranteed provider billing cap**. Metrics report estimates where usage is available; OpenAI billing is authoritative.
- Local disk and the browser's session cookie are required. Data has no automatic deletion or backup. Do not expose the Python listener publicly. The Vercel + Supabase version for private hosted testing is implemented in [hosting setup](docs/hosting.md); publishing and live verification are still pending.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s minhwa_workflow -v
node --check hosted_web/app.js
```

Current implementation evidence, live runs, owner feedback and remaining rollout checks are in [generation QA](docs/generation-qa.md). Automated tests use mocks; live trials are recorded separately. Physical print certification, a diverse pet benchmark, real payment processing and production hosting require separate validation.

Design direction and hero provenance: [DESIGN.md](DESIGN.md), [reading nook](docs/reading-nook-dog-hero.md). The earlier [product specification](docs/product-spec.md) retains proposals; the current implementation section takes precedence for local behavior.
