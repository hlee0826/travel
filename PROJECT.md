# Korean Minhwa Pet Portrait Project

## Project home and source of truth

**Project status:** Foundation ready  
**Project version:** 1.0  
**Design-system version:** 1.2  
**Working title:** 한국전통민화 반려동물 초상화 / Korean Traditional Minhwa Pet Portraits

---

## 1. Project objective

Create commissioned portraits of individual pets that are immediately recognizable while being rendered through an accurate, coherent Korean 민화 visual language.

This is first and foremost a **portrait project**. The pet is the key character, emotional center, and highest-detail subject. Korean traditional painting controls the composition, material language, symbolic environment, palette, spatial logic, and brush treatment.

### Governing rule

> Preserve the pet’s identity, traditionalize its rendering, and make the surrounding world unmistakably minhwa.

If a motif, decorative element, or composition interferes with recognition, that element must change. The pet must not.

---

## 2. Priority hierarchy

1. **Individual pet likeness** — face geometry, eye spacing and color, markings, ears, muzzle, body proportions, tail, coat, characteristic posture, and expression.
2. **Traditional Korean painting integrity** — shallow symbolic space, hanji, ink, layered pigment, barim, fine organic contours, traditional palette, asymmetry, and visual rhythm.
3. **Meaningful symbolism** — a customer-selected wish translated into a coherent motif bundle.
4. **Decoration** — only details that support the portrait, tradition, and selected meaning.

---

## 3. Core project files

- [Full design guideline](GUIDELINE.md)
- [Machine-readable project configuration](project.yaml)
- [Customer intake template](templates/customer_intake.md)
- [Artwork brief and concept-card template](templates/artwork_brief.md)
- [Production record template](templates/production_record.yaml)
- [Portable image-generation workflow](minhwa_workflow/README.md)

The portable workflow was imported from
[`hlee0826/travel`](https://github.com/hlee0826/travel) at commit
`4b0f5d44de20a27150e53fded056c72b65eb9ab7` on 2026-11-05. It prepares
ordered identity and style-reference inputs for Codex image generation. It is
an implementation aid beneath this project's portrait-first approval process;
`GUIDELINE.md` remains the complete design-system authority.

The full design guideline is the authority for rendering, composition, symbolism, color, prompts, workflow, and QA. This file is the operational entry point.

---

## 4. Customer-facing product logic

Customers choose the **wish or intention** of the portrait. The studio translates that choice into an approved anchor motif, supporting element, movement element, layout, and palette.

### Core Wish Collections

| Collection | Primary intention | Typical anchor |
|---|---|---|
| Longevity & Health / 장수와 건강 | A long and healthy life together | Pine or peach |
| Love & Family / 사랑과 가족 | Affection, companionship, and belonging | Peony; camellia as contemporary interpretation |
| Protection & Good News / 수호와 길보 | Safety, guardianship, and welcome news | Pine with magpie or rock |
| Peace & Healing / 평안과 치유 | Calm, recovery, remembrance | Lotus |
| Prosperity & Celebration / 부귀와 축복 | Honor, flourishing, and milestones | Peony |
| Wisdom & Curiosity / 지혜와 호기심 | Learning, attentiveness, and aspiration | Reduced 책거리 |
| Renewal & Resilience / 새로움과 굳셈 | New beginnings and endurance | Plum blossom or bamboo |

The customer may optionally choose a compatible anchor motif, season, symbolism intensity, and one personal element. The studio retains control over hierarchy, count, placement, and compatibility.

---

## 5. Portrait-first production workflow

### Gate 1 — Intake and reference audit

- Complete the customer intake.
- Collect face, full-body, and side/three-quarter references.
- Record five to eight recognition anchors.
- Resolve conflicts in age, grooming state, markings, and coat length.

### Gate 2 — Identity study

- Produce the pet alone on a plain warm-hanji ground.
- Do not add motifs, calligraphy, or decorative scenery.
- Run the face-crop, silhouette, marking-map, and familiar-person tests.
- Require the internal automated identity and material gate to pass; keep the study private.

No symbolic design work proceeds until the likeness is approved.

### Gate 3 — Concept card

- Translate the selected Wish Collection into a motif recipe.
- Select layout, palette, symbolism intensity, and inscription reserve.
- Show motif meaning, exact count, placement, and visual hierarchy.
- Obtain concept approval.

### Gate 4 — Integrated artwork

- Place the approved pet identity inside the selected minhwa structure.
- Keep all motifs subordinate in scale, contrast, and detail.
- Protect the pet’s ears, muzzle, markings, paws, and tail from overlap.
- Apply unified hanji, pigment, barim, and contour treatment.

### Gate 5 — Final QA

- Pass the identity gate.
- Pass the tradition gate.
- Score at least 82/100 using the guideline rubric.
- Add verified calligraphy and seal in post-production.
- Archive prompt, references, model/version, seed, settings, and final decisions.

---

## 6. Required approval tests

### Identity gate

- Face-crop test passed
- Silhouette test passed
- Marking-map test passed
- Familiar-person recognition test passed
- Pet is the first focal point at thumbnail size

### Tradition gate

- The image reads as Korean minhwa without relying on costume, palace, or temple shorthand
- Space remains shallow, stacked, and symbolic
- Hanji, pigment layers, barim, and contour feel materially coherent
- Motifs communicate one wish and remain subordinate to the portrait
- No generic pan-Asian substitutions

---

## 7. Default artwork specification

```yaml
aspect_ratio: "4:5 vertical"
pet_frame_height: "52-62% full body; 60-72% bust"
quiet_space: "28-35% balanced default"
symbolism_intensity: balanced
anchor_motif_count: 1
supporting_motif_count: 1
movement_element_count: "1-3"
paper: "warm mulberry hanji"
finish: "matte ink and translucent layered pigment"
lighting: "diffuse, embedded in the paper"
text: "reserved blank area; verified calligraphy added later"
identity_qa_weight: "40/100"
minimum_total_qa_score: 82
```

---

## 8. Current deliverables

- [x] Research and visual analysis
- [x] Traditional/contemporary balance framework
- [x] Portrait-first doctrine
- [x] Motif and Wish Collection strategy
- [x] Color and material system
- [x] Master generation prompts
- [x] Production and QA workflow
- [x] Customer and production templates
- [x] Portable Codex image-generation handoff (`minhwa-anchors-v3`)
- [ ] First sample-pet identity study
- [ ] First Wish Collection concept series
- [ ] Generation-model calibration tests
- [ ] Print and color proof
- [x] Customer-facing three-garden selection presentation
- [x] Customer-facing concept gallery with three identity-locked Wish Collection demos
- [x] Experimental Integrated Garden Reference Library v2 with a 20-plate documented core, exploratory extensions, and direct-to-viewer calibration plates across peony, lotus, plum, and pine gardens

---

## 9. Decision log

### Decision 001 — Portrait priority

The pet’s individual likeness is the primary purpose. Traditional elements must support recognition and never override it.

### Decision 002 — Tradition through visual grammar

Authenticity comes from space, composition, hanji, pigment, line, symbolism, and restraint—not from placing the pet in costume or adding generic Korean decorations.

### Decision 003 — Curated motif selection

Customers choose meaning and may choose one compatible anchor motif. The studio curates supporting elements so the work remains culturally coherent and visually controlled.

### Decision 004 — Two-stage internal production

Pet identity is internally approved before symbolic composition. The customer sees only the completed garden portrait, while the private study separates likeness problems from art-direction problems.

### Decision 005 — Portable workflow integration

The `minhwa-anchors-v3` workflow is maintained in this main project as the
technical handoff for Codex image generation. Its source-photo and style-anchor
inputs do not replace the required identity study, customer intake, artwork
brief, approval gates, or QA record defined by this project.

### Decision 006 — Gallery samples preserve the approval sequence

Website gallery demos are developed as fictional pets with undecorated identity
studies before motif integration. They are labeled as sample artwork and do not
claim likeness to real customer pets. Their identity anchors, prompt summaries,
and QA records are stored with the project before publication.

### Decision 007 — Integrated Garden Reference Library remains a non-identity reference

The experimental `minhwa_workflow/reference_library_v2` set formalizes a
garden envelope and a pet-to-fauna interaction vector for composition selection.
Its fictional subjects demonstrate pose, material integration, and motif balance;
they do not replace intake, the private undecorated identity study, likeness tests,
the internal identity gate, the tradition gate, or the 82/100 final QA requirement.

### Decision 008 — Three customer-facing garden recipes (superseded runtime attachment model)

The website offers Peony & Butterfly, Lotus & Butterfly, and Pine & Magpie
gardens using the stable internal values `peony`, `lotus`, and `pine`. The
customer photo governs individual identity and photographed pose; references
govern material, motif, palette, composition, and symbolic space. Decision 010
replaces the earlier single-call photo-plus-six-reference attachment model.

### Decision 009 — Balanced pose calibration (library calibration history)

Each six-image runtime garden set uses a 2+4 pose balance: one fictional cat and
one fictional dog face directly toward the viewer, while four plates preserve
natural three-quarter, standing, reclining, and fauna-interaction compositions.
The direct plates correct the source library's sideways-gaze bias without
removing the appealing butterfly or magpie interactions. The customer photo
remains the only authority for the commissioned pet's actual pose and gaze.

### Decision 010 — Private identity study followed by whole-canvas synthesis

Workflow version `minhwa-gardens-v8` uses two image-generation calls. The first
uses only the customer photo to create an undecorated identity study on warm
hanji. Automated material and likeness gates lock the pet internally before
any garden is developed; the study is never exposed for customer approval. The second call uses the internally approved painted
study plus five role-specific references from the selected garden and repaints
the complete canvas from scratch. It must not paste, mask, preserve, or reuse
identity-study pixels. The original photograph remains final QA evidence.

Final synthesis follows a garden-specific composition contract. Peony and lotus
retain portrait-forward scales; Pine & Magpie limits a bust/reclining pet to
46–54% canvas height (42–50% full body), while the mature pine spans 55–75% of
canvas width and reads at least 1.35 times the pet height. Every garden preserves
28–35% quiet paper, subordinate support/fauna ranges, and a visual path that
returns to the pet. Separate hard gates cover material unity, painted pet treatment,
photographic shine, shared edge and light logic, pet/motif scale, quiet-space
distribution, safe margins, and overall wall-art harmony.

## 10. Recommended next production milestone

Select one real pet with three strong reference photographs and build:

1. an undecorated identity study;
2. three concept cards using different Wish Collections;
3. one fully rendered final portrait;
4. a scored QA review documenting what remained consistent and what drifted.

This first controlled case becomes the calibration standard for future commissions.
