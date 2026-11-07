# Image generation implementation and QA — November 5, 2026

Historical v4 evidence: the live runs below used four anchors. The current v5 pose-routing implementation and pending reference setup are documented in `../minhwa_workflow/README.md`; these historical results do not validate v5 branch quality or savings.

The local upload → generated painting → automated review/release (studio review if flagged) → owner approval → simulated order → exact download flow is implemented and tested. This report distinguishes software behavior, two real API runs, owner feedback, and production-readiness work that remains.

## Requirement evidence

| Requirement | Implemented behavior | Evidence |
| --- | --- | --- |
| Actual pet upload | JPEG/PNG/WebP/HEIC decode, orientation, metadata removal, size/pixel limits, consent | HTTP validation tests; real source uploaded through browser |
| Appropriate photo | Structured one-pet, face and clarity check before painting | Bad-photo test makes zero image calls; both live photos accepted |
| Use the references | Original identity photo plus all four actual anchors; recorded hashes and ordered inputs | Provider payload tests; saved inputs for both live attempts |
| Their little world | Fresh botanical painting, coherent butterfly gaze, no source room or photographic cutout | Two live outputs visually reviewed; all nine automated criteria passed |
| Recognizable identity | Identity analysis, photo precedence, source comparison, correction choices | Owner rated first peony painting **4–5/5: recognizably my dog** |
| Safe retries | Original photo and anchors reused, previous paintings/order snapshots retained | Correction/retry and immutable-order tests |
| Refresh/recovery | Idempotent submission; persistent serial queue; uncertain requests held without automatic repeat | Queue/recovery tests; live lotus page refreshed during painting, one attempt recorded |
| Approval gates | All nine checks true releases artwork automatically; flagged candidates stay private; customer approval still gates checkout | Passing release, flagged media/order rejection and unchecked checkout rejection tests |
| Exact downloads | Saved named PNG/JPEG master; separate watermarked preview | Actual browser PNG and JPEG downloads matched corresponding masters byte-for-byte |
| 12 × 16 framing | 4:5 painting centered on 3:4 paper, no crop | Pixel equality test for inner painting; natural-oak mockup inspected on narrow screen |
| Limits/privacy | Session ownership, origin/host guards, reference validation, attempt/day reservations | HTTP and mocked provider tests; credentials never sent to browser |

## Automated validation

- **21 main tests + 3 portable workflow tests passed after automatic release was added.**
- JavaScript syntax check passed.
- Tests cover consent, idempotency, queue ordering/recovery, private media, pending-art rejection, explicit review overrides, uncertainty reconciliation, reservation limits, correction provenance, invalid dimensions, strict/incomplete model output, immutable downloads, English/Hangul name rendering, non-cropping matting, product preference persistence, reference integrity and cost estimates.
- Tests use provider mocks. They do not establish a statistical likeness success rate.

## Live API runs

Both used the same distinct dog photo, not two different dogs. Output: 2432 × 3040 PNG, high quality, `gpt-image-2.6-sunburst`; checks: `gpt-5-mini`.

| Garden | Job / attempt | Time for checks + painting | Estimated API cost | Result |
| --- | --- | --- | --- | --- |
| Peony | `799bad850df1e4bd5bed5420` / `9bcf440a73247ef5` | 84.3 s | $0.172252 | Automated checks passed; Codex visual QA passed; owner likeness 4–5/5 |
| Lotus | `ead5b6e7ba611d1df2cee7fd` / `bc0da095141c842f` | 80.8 s | $0.171658 | Automated checks and Codex visual QA passed; owner acceptance pending |

Combined estimate: **$0.343910**. Estimates use returned token usage and November 5 official pricing, not an invoice. Studio approval/wait time is excluded. No automatic retry occurred. Each job has one attempt and retains its original photo and all four anchor references.

Both results show coherent painted gardens and a changed head direction toward a butterfly, without the source room or pasted photographic pet. Codex noted stronger white chest/toe areas than the source; preserve owner approval as a real gate. An automated all-pass is advisory, not a guarantee. The `codex-qa` review record does not claim human-owner acceptance.

## Browser and download evidence

- New real lotus upload selected framed / 12×16. Those choices survived generation and reload.
- Reload during painting did not duplicate the request; the saved job has exactly one attempt.
- Side-by-side photo comparison, correction controls and disabled approval-dependent actions were inspected.
- Narrow, mobile, tablet and desktop layouts were checked. Requested viewport widths 320/390/768/1440 rendered as CSS widths 338/416/836/1583 in this browser configuration; at each observed width, document content width matched viewport width with no horizontal overflow. These are emulated layouts, not physical-device certification.
- No warning/error entries were reported by the browser log check. Temporary viewport override was reset.
- Test framed order `60a6179e6519e797348bface` (`MH-60A617`) totals $115 simulated; actually charged $0.
- Actual browser downloads `/Users/stevenlee/Downloads/pet-minhwa.png` and `.jpg` are both 2432 × 3040 and byte-identical to their saved approved master files.
- PNG SHA-256: `711a2aaefc1d6b234ca67f42949444768f2ee2a4c7ffedeb0cdfbfac0529f02f`
- JPEG SHA-256: `73791e505a5b1e87f8096edbaebd4d2a6ee65a7d9ad61fed029ccebca8430c3a`

Screenshots: `output/qa-desktop-lotus.png`, `output/qa-desktop-comparison.png`, `output/qa-mobile-comparison.png`, `output/qa-tablet-frame.png`. Key permission evidence: `output/openai-review-permission.png` (no secret key displayed).

## Before public rollout

The proposed **30-photo benchmark is not complete**. Only one distinct supplied pet photo is available. This pilot cannot establish reliability across cats, breeds, coat patterns, ages, blur, or difficult poses. Collect 30 consented photos, including cats and dogs with varied coats and poses; have owners rate likeness and reviewers rate art direction. The proposed target remains at least 24/30 with an acceptable painting within the allowance and both ratings ≥4/5. Record failures, attempts, latency and cost per accepted result; do not substitute synthetic examples for owner-rated evidence.

Physical proofing remains necessary at each offered size. The 12×16 sheet is approximately 203 pixels per inch, not 300; the 16×20 painting approximately 152. No upscaling is used to imply recovered detail. Supplier templates, bleed, color profile, materials and frame outer dimensions are not certified.

Public hosting, production authentication/storage/retention/backups, payments, provider-budget enforcement and fulfillment are separate rollout work. The local file queue is persistent on this disk but is not a distributed job service; corrupt storage requires operator repair. API reservation limits are admission controls, not a billing hard cap. The current server must stay on localhost.

## Automatic release update

After the owner encountered the manual pause during testing, passing artwork now proceeds directly to customer review. All nine criteria must be exactly true. The existing artifact renderer creates the named immutable master before release, and the audit record identifies reviewer `automated`. No extra provider call or automatic regeneration is added. Flagged results keep their manual review requirement, and incomplete assessments or artifact failures remain held. Tests cover both routes, exact exports, retry limits and required customer approval. The earlier live runs above used manual release; they are not evidence of a new live automatic-release run.

## Local testing allowance adjustment

Five attempts reserved the original $15 admission allowance while known provider cost was estimated at $0.852149. The private local configuration was increased to $30 (ten $3 reservations per rolling 24 hours) for continued testing. The default example remains $15. Session/photo/portrait limits remain active. The server was restarted while idle and the next global reservation was checked without submitting a paid request.


## November 7 pose routing validation

V5 implements compact eight-bucket classification, one or two selected references per garden/bucket, saved selection recovery, branch-specific gaze review, and explicit unavailable-composition handling. All real reference entries remain pending.

54 tests passed across the application and portable workflow suites, including the disposable UTF-8 PostgreSQL integration tests and local Caddy password proxy. Tests cover all eight selections in both gardens, strict classification schema, pending/missing references, no repeat request while a branch is unavailable, catalog changes between hosted stages, changed reference bytes, manual preparation, and preserved approved downloads. JavaScript syntax, Python compilation, and source-package catalog/privacy checks also passed.

Provider responses were mocked. No paid API calls or deployment were performed for v5; real pose classification, visual quality, and cost savings remain unmeasured.
