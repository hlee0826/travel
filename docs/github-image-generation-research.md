# GitHub research: pet-photo to minhwa artwork

Research observed November 4, 2026 (America/Chicago; November 5 UTC). Scope: image generation and image finishing for a customer website selling downloads and printed/framed pet artwork. This report makes a technical recommendation; it does not implement the product.

## Recommendation

**Use ComfyUI as the first private image-generation worker and workflow-development tool.** It offers reusable visual workflows, image editing, reference conditioning, masks, upscaling, and an API. That makes it the most direct way to evaluate likeness and minhwa style before committing to a custom inference implementation. Keep the consumer upload, preview, checkout, orders, downloads, and print fulfillment in the website application. This is an engineering judgment based on its documented capabilities, not a claim that ComfyUI supplies an entire commerce platform. [ComfyUI repository](https://github.com/Comfy-Org/ComfyUI)

Its server exposes image upload, queued workflow execution, history, and progress updates. Submit only a fixed, versioned workflow from the website's backend; customers should supply photos and approved product choices rather than arbitrary workflows or executable extensions. Run it behind the application's authentication and order controls. The isolation recommendation is a proposed architecture, not a claim that the documented API already provides all production controls. [Official server API](https://docs.comfy.org/development/comfyui-server/comms_routes)

**Diffusers is the strongest alternative for a team that wants to own a Python inference service from the outset.** Do not integrate both engines for the initial product. Choose Diffusers instead if the production team values direct code control over visual workflow iteration. Its library and documented reference-image adapters provide a credible basis for that choice. [Diffusers repository](https://github.com/huggingface/diffusers), [IP-Adapter documentation](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter)

## Shortlist

All four shortlisted projects exceed 30,000 stars in the observed primary sources. Stars and forks are measures of public interest and ecosystem activity; they do **not** establish active installations, paying customers, uptime, security, or quality on this pet-art task. No comparable verified active-user counts were found in the sources reviewed.

| Repository | Observed stars / forks | Source-code license | Relevant role and production fit |
|---|---:|---|---|
| [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | 145,038 / 17,260 | GPL-3.0 | **Main choice:** develop and execute controlled image-editing workflows. Requires a separate customer application and deployment operations. Counts and license from [GitHub API](https://api.github.com/repos/Comfy-Org/ComfyUI). |
| [huggingface/diffusers](https://github.com/huggingface/diffusers) | Approximately 34.9k / 7.5k | Apache-2.0 | **Alternative inference foundation:** Python pipelines suited to application-owned generation logic; requires building the service around the library. Counts and license are from the repository page. |
| [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | 165,236 / 31,917 | AGPL-3.0 | **Evaluation tool, not the preferred new commerce backend:** mature Stable Diffusion browser interface and API ecosystem, but the observed maintenance cadence and different license warrant attention. Counts/license from [GitHub API](https://api.github.com/repos/AUTOMATIC1111/stable-diffusion-webui); API documented in [official wiki](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki). |
| [xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Approximately 37.4k / 4.5k | BSD-3-Clause | **Optional finishing component:** image restoration/upscaling after artwork approval. It is not a photo-to-minhwa generator, and increased pixel dimensions do not prove print quality. Counts/license and restoration scope from the repository page; print-fit judgment requires samples. |

Do not treat a repository's code license as a blanket license for every downloaded model, adapter, extension, reference image, or resulting artwork.

## Maintenance evidence and freshness

| Project | Evidence observed | Interpretation |
|---|---|---|
| ComfyUI | API `pushed_at`: 2026-11-05 00:06:48 UTC; `updated_at`: 2026-11-05 00:52:47 UTC. Release page displays v0.44.0, November 4. [API](https://api.github.com/repos/Comfy-Org/ComfyUI), [releases](https://github.com/Comfy-Org/ComfyUI/releases) | Recent activity. Pin a tested release/workflow rather than automatically tracking development. |
| Diffusers | Latest release page displays v0.42.1, October 27, a fix for component-loading behavior that could bypass `trust_remote_code`. [Release](https://github.com/huggingface/diffusers/releases/tag/v0.42.1) | Recent release and security maintenance. Include that fix when choosing a tested version. |
| AUTOMATIC1111 | API `pushed_at`: 2026-03-02 07:00:53 UTC; `updated_at`: 2026-11-03 23:02:35 UTC. [API](https://api.github.com/repos/AUTOMATIC1111/stable-diffusion-webui) | A recent repository metadata update is not a recent code push. Less recent push evidence than ComfyUI. |
| Real-ESRGAN | Commit listing's newest visible default-branch commit is April 2, 2024; latest release shown is v0.3.0. [Commits](https://github.com/xinntao/Real-ESRGAN/commits/master/), [releases](https://github.com/xinntao/Real-ESRGAN/releases) | Older visible maintenance; validate runtime compatibility before adopting it. |

The browser labeled the ComfyUI API, current repository pages, and release pages as crawled “today”; AUTOMATIC1111's API was labeled “yesterday.” Real-ESRGAN's commit listing was labeled “last month.” Some older search results showed smaller ComfyUI counts; the newer API result takes precedence. Exact API counts were unavailable for Diffusers and Real-ESRGAN, so their displayed rounded figures are retained. Release pages omit the year in their rendered date; the report preserves those displayed month/day values instead of inventing a timestamp. API `pushed_at` is evidence of a repository push, not proof of the latest default-branch code change.

## Model and likeness implications

An execution engine does not itself learn minhwa or preserve a particular pet. The initial evaluation should compare a small, fixed photo-conditioned workflow against a representative set of dogs and cats with distinct face shapes, eye colors, markings, and coat types. This is a proposed acceptance test, not an already measured result.

A concrete baseline worth testing is SDXL image-to-image with a general IP-Adapter Plus reference input, controlled denoising, and a fixed minhwa art direction. The official Diffusers guide documents photo conditioning with text prompts and adjustable strength; the general IP-Adapter model card describes Plus variants as closer to the reference image. Those sources support trying the approach, but neither establishes reliable pet identity preservation. [IP-Adapter guide](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter), [general IP-Adapter model card](https://huggingface.co/h94/IP-Adapter)

Treat SDXL + IP-Adapter as a baseline to beat, not a final model selection. Compare newer image-editing models supported by the chosen engine on the same pet-photo set, then select on likeness, style fidelity, latency, per-approved-image cost, and applicable license terms. No model inference or cost benchmark was run during this research.

Specific licensing evidence:

- The SDXL base model identifies its license as CreativeML Open RAIL++-M, distinct from either engine's code license. Its terms include use restrictions and output provisions. Record the exact checkpoint and its terms before launching paid downloads or prints. [Model card](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0), [license](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md)
- The general `h94/IP-Adapter` card labels its weights Apache-2.0. Record the particular adapter and image encoder as separate components. [Model card](https://huggingface.co/h94/IP-Adapter)
- **Do not substitute IP-Adapter-FaceID for the general adapter in the commercial baseline.** Its own card states that it is intended for research rather than commercial use because of the InsightFace pretrained-model terms. Its human-face workflow also provides no pet-likeness validation. [FaceID model card](https://huggingface.co/h94/IP-Adapter-FaceID)
- Any minhwa LoRA, third-party checkpoint, custom node, or upscaler model needs its own provenance and terms review. Training a style adapter is a later option only if prompting and reference conditioning cannot meet the quality target; this research did not identify or approve a minhwa-specific checkpoint.

## Scope for the product specification

Proposed requirements that follow from the findings:

1. Preserve the uploaded original and show artwork beside it for customer approval. Define likeness by recognizable markings, face/ear shape, coat and eye color, not merely animal species or breed.
2. Approve one artwork version before fulfillment. Digital delivery and the print order must reference that same immutable approved asset.
3. Make print sizes conditional on validated pixels, crop, and the print provider's requirements. Inspect physical sample prints; do not promise that upscaling restores missing detail.
4. Keep style/workflow/model versions with each generation, plus seed and relevant settings, so failures can be investigated.
5. Handle job failure, retry limits, access-controlled photo storage, upload validation, retention/deletion, payments, download authorization, and fulfillment independently of the generation UI.
6. Start with one generation engine and one approved workflow. Add another engine, per-pet training, or an upscaler only after measured failures justify the extra operation and maintenance.

## Considered but not shortlisted

[InvokeAI](https://github.com/invoke-ai/InvokeAI) is relevant: it provides a creative canvas, image editing, and workflows. The observed repository result showed approximately 28.2k stars (crawler label: “last month”), below this report’s chosen 30k-star cutoff, so it is excluded while four qualifying alternatives exist. That threshold is a selection rule, not evidence that InvokeAI is an inferior product.

## Unresolved before implementation

Pet likeness and authentic minhwa quality remain unproven; no GPU run, upload flow, paid order, or physical print was tested. Exact model/adapter/node choices and commercial rights remain selection work. A framework shortlist cannot establish product demand, conversion rate, profit margin, or cost per approved order.
