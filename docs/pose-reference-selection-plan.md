# Minhwa Pose Based Reference Selection Plan

Status: Eight-bucket implementation complete in the workspace; reference assets and live validation pending.

Use the existing LLM photo review as a lightweight classifier: check basic photo suitability and match the pet to one of eight predefined pose buckets. Map that bucket to a small reference set within the chosen Peony or Lotus garden. Use that selection consistently for painting and final artwork review.

The primary objective is more predictable composition and likeness. Lower image-input cost is a secondary objective to measure. Reference images will be supplied later; branches remain inactive until their assets are ready.

# Scope and design decisions

- Keep one shared generation pipeline. Branches select references and instructions; they do not duplicate the pipeline.
- Extend the existing photo assessment rather than adding a second LLM call.
- Use exactly eight pose buckets: standing, sitting, reclining, and head/chest portrait, each with front and profile variants.
- Ask for the bucket directly, not separate posture, angle, coverage, visibility, or confidence reports.
- Target one or two strong references per selected set. Do not automatically attach the current four shared anchors.
- Preserve the photographed pose category and recognizable features while painting a new garden.
- Keep new branches unavailable until their references are supplied and validated.

# Current code behavior

The existing photo reviewer checks for one identifiable cat or dog, face visibility, clarity, identity, and unseen features. Both local and hosted pipelines already run photo review, painting, and artwork review.

The shared workflow always supplies four anchors and instructs every animal to turn toward a butterfly. The final reviewer also requires butterfly interaction and a fresh pose. Both instructions must change for front-facing compositions to work correctly.

The local server prepares reference inputs before assessment, while the hosted pipeline rebuilds inputs between stages. The revised flow must resolve references after assessment and preserve the exact selection through each attempt.

# Photo assessment

The assessment answers one routing question: which of the eight buckets best fits this photo? It is not a detailed description of the animal or scene.

Return only:

- `usable`: whether there is one identifiable cat or dog with a sufficiently clear, visible face.
- `bucket`: one of the eight allowed identifiers below, or null when no safe match is possible.
- `reason`: empty on success; one short explanation when the photo is unsuitable or cannot be matched.

Do not request breed, eye color, individual markings, detailed anatomy, left/right orientation, separate angle fields, confidence scores, or an identity narrative. The original photo continues to supply identity directly to generation and final review. Replace downstream dependencies on the current identity narrative and detailed suitability fields when implementing this compact response.

Use a strict response schema and server-side validation. A null bucket is a stop condition, not a ninth reference bucket. Do not force an unsupported classification.

# Routing rules

Give the classifier a short rubric: use portrait buckets for head/chest crops or when the body is insufficiently visible; otherwise match the visible standing, sitting, or reclining posture. Use the face, not the torso, to choose front versus profile. Map three-quarter faces to the closest compatible bucket without requiring a large head turn. Do not infer unseen posture.

| Bucket | Matching photo | Art direction |
| --- | --- | --- |
| standing_front | Standing with a front-facing head | Standing, looking forward |
| standing_profile | Standing with a profile-compatible head | Standing, watching a butterfly |
| sitting_front | Sitting with a front-facing head | Seated, looking forward |
| sitting_profile | Sitting with a profile-compatible head | Seated, watching a butterfly |
| reclining_front | Reclining with a front-facing head | Reclining, looking forward |
| reclining_profile | Reclining with a profile-compatible head | Reclining, watching a butterfly |
| portrait_front | Head/chest framing with a front-facing head | Tighter portrait, looking forward |
| portrait_profile | Head/chest framing with a profile-compatible head | Tighter portrait, watching a butterfly |

Application logic is a direct lookup: if usable and the bucket is valid, load the selected garden’s reference set for that bucket. Otherwise stop before painting. Missing references produce a composition-unavailable message, not a bad-photo message. Never silently substitute another bucket.

Example: `{ "usable": true, "bucket": "standing_profile", "reason": "" }` plus Peony selection loads only the Peony standing-profile references. There is no second reasoning or classification call.

# Reference catalog and consistency

Use a small explicit catalog keyed by garden and bucket, with ordered reference files, reference roles, and pending/ready status. The same eight bucket identifiers apply to both gardens. A ready set must have readable approved assets. Empty entries are placeholders, never valid generation inputs.

Keep palette, brushwork, botanical drawing, paper treatment, and detail level consistent across sets. Do not add left/right subdivisions or extra assessment fields for the initial version.

The uploaded photo remains authoritative for identity and markings. Reference animals supply painting style and compatible composition. Generate image-number descriptions from the actual attachment list rather than assuming five total images.

Save the assessment, branch identifier, workflow and catalog versions, exact prompt, reference filenames, and hashes per attempt. Preserve the selection across stage resumptions, and stop if referenced assets change. Preserve existing approved artwork and order snapshots.

# Generation and final review

Generation and review must use the same saved composition instructions and reference set.

- Front-facing compositions: require a forward-facing head and gaze; butterflies may be decorative.
- Profile compositions: require a believable sightline toward the butterfly when interaction is selected.
- Portrait compositions: allow intentional chest framing while protecting the face and ears.
- Full-body compositions: check the selected posture, anatomy, and intended body visibility.
- All compositions: check likeness, markings, painted treatment, fresh garden setting, safe margins, and absence of generated text.

A fresh setting does not require a changed pose. Keep customer likeness approval. Make correction choices branch-aware so a frontal portrait does not offer a mandatory butterfly-gaze correction.

# Implementation work

| Area | Required change |
| --- | --- |
| generation.py | Replace detailed photo assessment with suitability and eight-bucket classification; make final review branch-aware |
| minhwa_workflow/workflow.py | Add deterministic selection and reference catalog; build prompts from the selected set |
| server.py | Use compact suitability result; remove identity-narrative dependencies; persist bucket and references; adapt local/manual preparation and metadata |
| hosted/pipeline.py | Use compact suitability result; remove identity-narrative dependencies; save and reuse selection across durable stages |
| hosted_web/app.js | Remove fixed reference-count wording; adapt corrections and unavailable-composition messages |
| Deployment packaging | Include catalog and branch assets; remove assumptions that exactly four anchors exist |
| Tests and documentation | Update fixed-reference fixtures, portable handoff instructions, workflow version, and routing expectations |

The standalone/manual path must accept an explicit assessment or retain an explicitly identified legacy workflow. It must not silently claim to have performed an API assessment. Existing jobs keep their recorded workflow; new attempts use a clearly recorded version. Keep private assessments out of customer-facing job responses except for a concise safe summary.

# Validation and rollout

## Phase 1 Build the routing foundation

- [x] Replace detailed photo assessment with usable, one of eight bucket identifiers or null, and a short failure reason.
- [x] Implement shared routing and pending reference entries.
- [x] Connect local and hosted generation and review to the same saved selection.
- [x] Update manual handoff, customer copy, deployment packaging, and documentation.
- [x] Test all eight routing outputs, uncertain classifications, missing references, and front/profile review instructions with mocked assessments.
- [ ] Validate actual classification of mixed head/body angles and cropped bodies on real photos.
- [x] Verify stage resumption preserves selection and changed references block painting or review.
- [x] Verify previous approved paintings and order snapshots remain intact.

## Phase 2 Add and assess reference sets

- [ ] Supply and curate references for each initial supported set.
- [ ] Label a small varied collection of consented pet photos with expected branches.
- [ ] Compare the current four-anchor approach and the new selected sets using the same photos and comparable generation settings.
- [ ] Track routing accuracy, likeness, posture compliance, style consistency, acceptance rate, latency, and actual API usage.
- [ ] Activate only sets that demonstrate acceptable results within the eight-bucket catalog.

# Cost and success criteria

Measure cost per accepted portrait: total review and generation spending divided by the number of accepted portraits. Include failed attempts and regenerations.

Sending fewer references should reduce image-input usage when other settings are comparable. It does not proportionally reduce total cost: the source photo, generated artwork review, and output generation still incur costs. The compact classifier reuses the existing photo-review call and avoids a detailed written assessment; measure its actual usage rather than assuming savings. [OpenAI image input cost documentation](https://developers.openai.com/api/docs/guides/images-vision#calculating-costs)

The change succeeds if it maintains or improves likeness and style consistency, reliably follows selected compositions, and lowers cost per accepted portrait without increasing rejection or retry rates. Structured routing improves control over inputs; visual consistency and exact composition remain model limitations. [OpenAI image generation limitations](https://developers.openai.com/api/docs/guides/image-generation#limitations)

Keep the initial scope to eight buckets. Additional classification detail or branches require evidence that the current buckets cannot handle a meaningful set of photos.
