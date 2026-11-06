# Minhwa Studio

Main repository: [hlee0826/travel](https://github.com/hlee0826/travel). Live private preview: [minhwa.pinnedby.com](https://minhwa.pinnedby.com).

> Hosting: the Vercel + Supabase implementation and deployment instructions are in [docs/hosting.md](docs/hosting.md). The local studio below remains supported.

# Local development

A functioning local pet-art studio: upload a face photo and full-body photo of the same cat or dog, generate a new minhwa-inspired painting, review it, choose a keepsake, and download the approved artwork. Checkout and fulfillment remain simulated. The server binds only to this computer.

## Start

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python server.py
```

Open http://127.0.0.1:4187. No frontend build is required. Configuration is read at startup from private `.env.local`; environment variables override it. Copy `.env.example` for a new installation. Never put credentials in browser code or job records. Keep `.env.local` owner-readable only.

API mode requires `MINHWA_IMAGE_PROVIDER=openai`, `OPENAI_API_KEY`, Images Request and Responses Write permissions. The configured image model is `gpt-image-2.6-sunburst`; photo/artwork checks use `gpt-5-mini`. Requests use API credits. `MINHWA_IMAGE_PROVIDER=manual` retains the Codex handoff. See [API setup](docs/openai-api-setup.md).

## Working flow

1. Upload one face photo and one full-body photo of the same pet. JPEG, PNG, WebP or HEIC files may be up to 20 MB / 40 megapixels each and must be at least 600 pixels on each edge. Consent is required. Files are decoded, orientation-corrected, normalized and stripped of metadata.
2. A joint photo check requires one identifiable cat or dog, confirms both photos show the same pet, and checks facial clarity, body visibility and markings. Rejected photos never reach the image endpoint.
3. The durable local queue creates one high-quality 2432 × 3040 painting using both photos plus all four actual style references. The face photo governs facial geometry and expression; the full-body photo governs silhouette, proportions, coat and markings. No previous output is used as a retry reference.
4. Automated review checks facial likeness and expression, markings, body proportions, anatomy, painted appearance, fresh setting, chosen garden, scene interaction, safe margins and unwanted text. A result that passes every check is released automatically for customer review. Any failed or uncertain criterion stays private for explicit studio review.
5. The customer compares the approved painting with their face photo and explicitly approves it. Corrections can request a fresh interpretation while retaining earlier approved work.
6. Choose digital, print or natural-oak framed print. Physical sizes are 8 × 10, 12 × 16 and 16 × 20 inches. Place a clearly labeled test order; no payment or supplier is contacted.
7. PNG/JPEG downloads use the saved approved master, including the optional name. The preview watermark is separate. A 12 × 16 sheet centers the complete 12 × 15 painting with half-inch top/bottom borders; it never crops the artwork.

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

`minhwa_workflow/workflow.py` is the authoritative `minhwa-anchors-v5-two-photo-identity` brief. Image 1 supplies face identity and expression; image 2 supplies body proportions, coat and markings. Images 3–6 supply pigment, botanical drawing, composition and negative space. All four anchors are included for either garden. Original anchors remain unchanged; the bamboo advertisement's outer margins are cropped only for API transmission. Inputs are normalized/downscaled for transmission, with original hashes recorded. Missing or changed references block generation.

The pet and plants must share a traditional painted language, with the pet watching one nearby butterfly. No source-room background, photographic cutout, copied anchor identity, text, seal or signature. Optional names are rendered once into the master with bundled OFL-licensed Noto Serif KR. Likeness is reviewed, not mathematically guaranteed.

`.studio/jobs/JOB_ID/` retains the normalized face and body sources, attempts, prompts, reference hashes, provider metadata, review findings and approved artifacts. Pending/rejected artwork and raw masters are not public static files. Session ownership restricts media, orders and downloads. Existing approved orders keep immutable snapshots.

## Reliability and limits

- One process owns the worker. Atomic file writes and a cross-process storage lock coordinate the server and studio CLI. Queued jobs survive restarts; in-flight work is held for reconciliation rather than repeated.
- Duplicate upload and checkout submissions are idempotent. Refreshing or changing pages does not trigger generation.
- Maximum three attempts per portrait, three per identical photo per day, six per session per day, and two accepted paintings per portrait.
- Each attempt reserves $3 against a default $15 rolling 24-hour admission allowance (`MINHWA_DAILY_BUDGET_CENTS`). Failed/uncertain attempts retain their reservation. This is a conservative request allowance, **not a guaranteed provider billing cap**. Metrics report estimates where usage is available; OpenAI billing is authoritative.
- Local disk and the browser's session cookie are required. Data has no automatic deletion or backup. Do not expose the Python listener publicly. The Vercel + Supabase version for private hosted testing is implemented in [hosting setup](docs/hosting.md); publishing and live verification are still pending.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s minhwa_workflow -v
node --check hosted_web/app.js
```

Current implementation evidence, live runs, owner feedback and remaining rollout checks are in [generation QA](docs/generation-qa.md). Automated tests use mocks; live trials are recorded separately. Physical print certification, a diverse pet benchmark, real payment processing and production hosting require separate validation.

Design direction and hero provenance: [DESIGN.md](DESIGN.md), [reading nook](docs/reading-nook-dog-hero.md). The earlier [product specification](docs/product-spec.md) retains proposals; the current implementation section takes precedence for local behavior.
