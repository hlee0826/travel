# Pet Minhwa Website Product Specification Draft

Editable Page: https://chatgpt.com/space/page_c75f8468557481919cf51623b68ffc80

Draft v0.1 • November 4, 2026

Build an English-language website for US customers that transforms pet photos into personalized, Korean minhwa-inspired artwork. Customers can purchase a digital download, an unframed print, or a framed print. The defining quality is a pet that remains recognizable within a cohesive painted composition.

The three product formats and US-first English launch are confirmed. The November 5 API pilot connects OpenAI directly; ComfyUI is the earlier planned workflow engine and is not installed. The scope, quantities, sizes, and commercial approach below are proposed defaults for the first version.

# Current local implementation — November 5, 2026

This section supersedes conflicting proposals below. The functioning local build uses OpenAI Images plus Responses photo/art checks, one customer identity-and-pose photo, and six curated references from the selected peony, lotus, or pine garden. It creates one candidate per attempt through a persistent single-worker disk queue, automatically releases artwork only after every garden-aware check passes, routes flagged results to studio review, and still requires customer approval. Limits are two accepted paintings and three attempts per portrait. Outputs are 2432 × 3040; approved PNG/JPEG masters are immutable. Physical choices include 12 × 16 paper with a centered uncropped 12 × 15 painting. Names use a bundled licensed English/Hangul font. Payment and fulfillment are simulated; ComfyUI is not installed. See `README.md` and `docs/generation-qa.md` for exact current behavior, tests and rollout gaps.

# Customers and product promise

Serve pet owners buying a keepsake for themselves or a gift. The customer should be able to upload a photo, choose an art direction, approve their portrait, and buy without writing prompts or understanding image-generation settings.

Describe the work as AI-generated, minhwa-inspired pet portraiture. The product should evoke the supplied references while establishing its own compositions and visual identity.

# Art direction from the supplied references

The five reference images establish the following visual targets:

| Reference | Observed direction | Product implication |
| --- | --- | --- |
| 1 and 2 | Black-and-white and tabby cats, peonies, butterflies, aged cream paper, small vertical Korean names and red seals | A floral composition with strong coat-pattern fidelity |
| 3 | Corgi in side view, lotus leaves and flowers, ochre paper and muted green | A lotus composition that supports the original pose |
| 4 | Seated white dog, red and white peonies, birds and butterflies, tall composition | An example of full-body framing and controlled decorative density |
| 5 | White dog among bamboo, broad leaves and rocks, muted pink ground | A possible later botanical direction; the surrounding promotional text is not part of the artwork |

Preserve the pet’s recognizable ear silhouette, face and muzzle proportions, eye color, age, coat patches, and body proportions. Use the photo only as an identity reference to create a new traditional Korean painting. Paint simplified matte pigment shapes, expressive ink contours, broad deliberate brushwork, restrained flat shading, and subtle hanji paper. Group fur into color masses with only a few accents. Avoid photorealistic fur, camera lighting, glossy realism, and photo textures beneath a paper or watercolor filter. Keep the pet and plants in the same painted visual language.

Launch with two curated compositions: **Peonies and butterflies** and **Lotus garden**. Use the four selected reference images as actual image inputs for style and overall composition: the tuxedo and tabby cats with peonies, the corgi with lotus, and the white dog among bamboo. Store them in `minhwa_workflow/style-anchors/`. Peony compositions emphasize the two peony anchors; lotus compositions emphasize the lotus anchor. All four guide pigment, botanical drawing, flattened space, scale, and negative space. Adapt their compositions into a new painting without borrowing the depicted pets’ identities or copying text, watermarks, signatures, pet names, seals, or promotional borders. Use original or appropriately licensed supporting assets. Add the customer’s optional pet name after image generation using a licensed font with English and Hangul support, with an exact text preview.

# First version scope

| Include at launch | Defer |
| --- | --- |
| One cat or dog per artwork | Multiple pets, people, and other species |
| One primary photo per generation | Combining several reference photos |
| Two art directions and one portrait aspect ratio | Freeform prompt editing and a large style library |
| Two preview candidates and one optional retry batch | Unlimited regeneration and subscriptions |
| Optional pet name | Custom calligraphy services and artist commissions |
| Digital, unframed, and framed purchase paths | Canvas, merchandise, gift packaging, and international shipping |
| Mobile-friendly creation, checkout, and order status | Native mobile apps and a public social gallery |

Proposed upload boundary: JPEG, PNG, or HEIC; maximum 20 MB and 40 megapixels per image. Correct orientation and convert supported inputs before generation. Recommend at least 1,500 pixels on the long edge; flag blur, obscured faces, or cropped ears and paws. Reject corrupt or unsupported files and photos containing no identifiable pet or multiple pets. Let customers replace the photo without losing their selected style.

# Customer journey

1. **Discover.** Show example transformations, all three purchase formats, prices, and a concise explanation of minhwa-inspired art. Use approved examples with permission.
2. **Upload.** Provide simple photo tips and a crop preview. Ask customers to confirm they may use the photo.
3. **Personalize.** Choose one of two compositions and enter an optional name. Compose a new pose with the pet looking toward a butterfly: its head, muzzle, and pupils should share a clear sightline to that butterfly. Preserve identifying features while allowing pose and composition to change. Do not invent unseen identifying markings from a cropped source.
4. **Generate.** Show queued, generating, ready, or failed status. Preserve progress across a refresh. Show a time estimate only after measuring real performance.
5. **Review.** Present two watermarked previews beside the original. Let customers select one, use their one retry batch, or change the input. Changing the input starts a new session subject to abuse limits.
6. **Choose a product.** Select digital, print only, or framed print. For physical products, choose a supported size and see the exact crop plus a clearly labeled frame mockup.
7. **Approve and pay.** Approve the final artwork, name, and crop. Show the complete price, shipping, taxes, and delivery estimate before payment.
8. **Receive.** Unlock the purchased digital file after verified payment. For physical purchases, show production and tracking status and provide a support route.

Proposed commercial flow: a limited free watermarked preview followed by payment for the chosen product. Require email verification before generation and apply per-session, per-account, and service-wide spending limits. A failed generation does not consume the customer’s retry allowance. Pricing remains open until generation cost and print quotes are measured.

# Products and delivery files

| Product | Customer receives | Proposed launch configuration |
| --- | --- | --- |
| Digital download | Unwatermarked full-resolution artwork in PNG and high-quality JPEG, with dimensions and suggested maximum print size | One approved portrait |
| Print only | Physical art print without a frame, plus the digital download | 8 × 10 and 16 × 20 inches |
| Framed print | The same approved art, printed and framed, plus the digital download | Same two sizes; one neutral frame finish initially |

Including the digital file with physical orders is a proposed bundle decision. Final paper, frame finish, glazing, mat, sizes, prices, and shipping coverage depend on the selected supplier. State whether dimensions describe the print or the outside of the frame.

Use a consistent 4:5 portrait composition to support the proposed sizes without a new crop. At a target of 300 pixels per inch, an 8 × 10 print needs 2,400 × 3,000 pixels and a 16 × 20 print needs 4,800 × 6,000 pixels before any supplier-required bleed. Changing DPI metadata alone does not create image detail. Check the enlarged output for altered eyes, markings, whiskers, and text.

Create separate preview, downloadable master, and supplier-specific print files. Keep names and important features inside the selected product’s safe area. Follow the supplier’s actual template, color profile, file format, and bleed requirements. Printful’s published guidance recommends 300 DPI, PNG/JPEG, sRGB, and product-specific templates; it is a candidate, not a selected supplier. [Printful file guidance](https://www.printful.com/create-digital-print-file)

# Generation and quality requirements

Use seven images with separate roles: the uploaded photo governs individual identity and visible pose; six references from the selected garden govern material, motif, palette, composition, and shallow symbolic space. Never use the uploaded photo as a pixel base, edit target, tracing, or background. Generate a fresh painted garden around the photographed posture without forcing the pet to look at a butterfly or magpie. The local MVP records the ordered image paths, role map, hashes, and creative prompt in each job’s `generation-inputs.json`; Codex must pass all seven actual files to its built-in image generation tool. Missing references block preparation rather than falling back to photo-only generation. Record `minhwa-gardens-v5` and the six selected filenames on new candidates. Check every candidate for traditional painting integrity, recognizable identity, pose fidelity, coherent anatomy, garden-specific motifs, pet dominance, and safe margins. Preserve approved candidates and order snapshots; revisions require fresh approval.

Keep names outside the generative pass so that spelling can be checked exactly. If preparing the large master changes the visible appearance, show it for renewed approval before printing. Keep the approved artwork version attached to the order.

Proposed pilot: 30 consented pet photos, split between cats and dogs and including dark coats, white coats, distinctive patches, long fur, short fur, and varied poses. Have the owner rate likeness and a reviewer assess the composition.

Release gates:

- At least 24 of 30 pilot inputs produce one acceptable portrait within two batches, with likeness and art direction each rated at least 4 out of 5.
- Every purchased result passes a visual check for extra or missing anatomy, changed coat patterns, distorted eyes, illegible text, and accidental signatures.
- Each offered print size passes a physical sample review for detail, paper color, dark fur, white fur, crop, and frame presentation.
- Log measured generation time, failure rate, accepted-result cost, and retry rate before setting a customer-facing service target.

These are proposed acceptance targets, not demonstrated model capabilities.

# Selected generation engine and GitHub shortlist

**November 5 API pilot: use OpenAI GPT Image 2.6 Sunburst directly through the website backend.** The original pilot sent the identity photo and four style anchors. The current `minhwa-gardens-v5` workflow sends the customer photo and six references selected for one of three gardens, then displays one generated candidate for approval. One request runs at a time; manual legacy jobs remain supported. The project key is server-side. See `openai-api-setup.md` for validation and limitations.

**Earlier engine decision, deferred during this pilot: ComfyUI.** Run it privately behind the website backend to execute a controlled pet-photo-to-minhwa workflow, with image conditioning, generation, and enlargement where needed. Customers use the website and do not interact with ComfyUI directly. Uploads, customer accounts, payments, downloads, and fulfillment remain in the website application. The underlying model and workflow settings will be selected through the art-quality pilot. Diffusers and AUTOMATIC1111 remain research alternatives, outside the initial implementation. [ComfyUI](https://github.com/Comfy-Org/ComfyUI), [server API](https://docs.comfy.org/development/comfyui-server/comms_routes)

The shortlist uses a 30,000-star minimum plus substantial fork counts as public adoption signals. These repositories meet that popularity filter; comparable active-user counts are unavailable, so “high usage” is not independently established. Counts below are observed GitHub snapshots during research on November 4, 2026, and may be rounded or cached.

| Repository | Stars and forks | Role |
| --- | --- | --- |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | 145,038 stars; 17,260 forks | Selected generation workflow engine for the first version |
| [Diffusers](https://github.com/huggingface/diffusers) | About 34.9k stars; 7.5k forks | Code-first alternative |
| [AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | 165,236 stars; 31,917 forks | Evaluation tool; less recent observed code pushes |
| [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | About 37.4k stars; 4.5k forks | Optional enlargement step, not the portrait generator |

ComfyUI uses GPL-3.0, Diffusers Apache-2.0, AUTOMATIC1111 AGPL-3.0, and Real-ESRGAN BSD-3-Clause, as reported by their repositories. Model weights, adapters, and extensions have separate terms. A popular repository does not guarantee a commercially suitable model or accurate pet likeness.

A possible baseline is SDXL with a general IP-Adapter reference input, compared against other image-editing models on the same photos. Do not select a model until the pilot passes. The general adapter and the similarly named FaceID adapter are different: the FaceID model card specifies research-only, non-commercial use. [General IP-Adapter](https://huggingface.co/h94/IP-Adapter), [FaceID model card](https://huggingface.co/h94/IP-Adapter-FaceID)

# Website and service structure

Keep one storefront and application backend, a persistent job queue, private image storage, a database, and an isolated ComfyUI generation worker. The browser talks to the application backend; generation credentials and internal workflow tools stay private.

Core records are a customer/session, source image, generation job, artwork version, product variant, order, payment reference, and fulfillment reference. Store the workflow/model version, output dimensions, and approved crop with each selected artwork.

The minimum screens are the landing page, creation flow, results and product selection, checkout, order/download page, and an operator view for failed generations, print approval, and order exceptions. Provide labeled controls, keyboard navigation, readable contrast, meaningful progress announcements, and a usable mobile upload experience.

# Payment and fulfillment behavior

Record payment, artwork readiness, and fulfillment as separate states. A successful browser redirect is not proof of payment: release downloads and create fulfillment work only after a verified payment event. Repeated payment or fulfillment events must not create duplicate charges or print orders.

For the initial launch, an operator checks paid print orders before releasing them to production. Submit the approved artwork version and selected SKU. An integration must distinguish submitted, accepted, in production, shipped, delivered where supported, and failed. Keep the customer informed if a paid order cannot be fulfilled; route it to support and refund or replacement handling.

Use a persistent order reference to reconcile uncertain supplier responses before retrying. Revalidate inventory, shipping eligibility, and pricing before checkout. Once production starts, explain any supplier-imposed cancellation limit in the purchase policy.

Printful’s API is a candidate integration with draft-order creation and a separate confirmation step. Supplier choice still depends on samples, US delivery coverage, total cost, and support. [Printful API documentation](https://developers.printful.com/docs/)

# Privacy and operational requirements

Keep original photos and purchased files private. Use expiring download links with ownership checks and a way to request a new link. Validate file contents and decoded dimensions, strip location metadata, and keep untrusted uploads away from executable paths. Keep secrets on the server and grant operators only the access needed for fulfillment and support.

Do not use customer photos for training or a public gallery without separate permission. Verify the generation provider’s data terms before selection. Proposed retention: delete unpurchased source photos and previews after 30 days; retain purchased masters for 12 months for downloads and reorders, with the retention period disclosed. Keep required order records separately from image retention and define deletion handling before launch.

Record generation failures, costs, payment events, print-file checks, supplier errors, and support outcomes without logging image bytes or unnecessary personal details.

# Pricing and success measures

Set prices only after measuring the cost of an accepted artwork, including discarded previews and retries. For each product, calculate contribution after generation, enlargement, storage, payment fees, print and frame cost, shipping subsidies, expected reprints/refunds, and support.

Track upload-to-preview completion, preview-to-purchase conversion, likeness acceptance, cost per accepted artwork, time to a ready preview, physical-product share, print rejection/reprint rate, and contribution per order. Evaluate free-preview economics separately because customers who never buy still incur generation cost.

# End to end acceptance checks

Before a paid beta, verify that an interrupted generation can resume, malformed uploads are rejected, exhausted retries cannot bypass the limit, and failed jobs preserve the allowance. Confirm that one customer cannot access another customer’s originals or downloads.

Exercise digital, unframed, and framed purchases. Test declined payments, repeated payment notifications, expired download links, unavailable product variants, and a supplier timeout after order submission. A repeated event must leave one paid entitlement and at most one physical order. Confirm that the printed file matches the customer-approved version, name, size, and crop.

# Delivery plan and open decisions

1. **Art feasibility.** Compare the shortlisted generation approaches on the pilot photos. Choose the model and workflow on likeness, reference-style fit, commercial terms, cost, and repeatability.
2. **Print proof.** Select a supplier through sample orders and validate every launch SKU.
3. **Private beta.** Build the complete upload-to-download and upload-to-print flows with manual print review.
4. **Launch.** Open paid access after quality, payment, privacy, and fulfillment checks pass.

Before implementation, decide the brand name, preview allowance and pricing, model/provider, print supplier, final sizes/materials, refund policy, and whether digital files are included with physical orders. The immediate dependency is an art-quality benchmark; popularity alone cannot establish whether a repository can preserve a particular pet’s identity.

## Supporting research

See [GitHub image generation research](github-image-generation-research.md) for source snapshots, adoption signals, maintenance evidence, and licensing details.

