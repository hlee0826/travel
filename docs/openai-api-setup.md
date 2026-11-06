# OpenAI API setup — November 5, 2026

The user approved the **Minhwa local testing** key in the **Minhwa Testing** project. It expires December 5, 2026. Original permissions were Images Request and List models Read. Responses Write was added with explicit user approval for photo and artwork checks; the saved setting was reopened and verified. No other permission or expiry was changed.

The key is only in owner-readable `.env.local`. Never print it, add it to job records, or expose it to the browser. The application uses verified HTTPS with certifi. No Files API permission is needed.

The Pro credit benefit was activated with explicit approval of its Codex API-key restriction. At activation, the dashboard showed $57 expiring November 23, 2026 and a scheduled $100 grant on November 23 subject to eligibility. That is an activation snapshot, not a current balance after testing. The restriction concerns using this organization's keys to authenticate Codex; subscription-based Codex and ordinary image/Responses requests remain available.

## Current integration

- Images: `gpt-image-2.6-sunburst`, `/v1/images/edits`, one opaque high-quality 2432 × 3040 PNG per attempt.
- Checks: `gpt-5-mini`, `/v1/responses`, strict structured output, `store:false`, photo first and artwork afterward.
- Five generation inputs: original pet identity photo and all four user-supplied painting references. Art review compares source, candidate and all anchors.
- `generation.py` handles private configuration and provider calls. `server.py` persists a serial local queue and automatically releases results only when every artwork check passes; flagged results wait for studio review. `studio.py` provides review, reconciliation and usage estimates.
- Calls are never automatically retried. Interrupted or ambiguous outcomes stay held for operator reconciliation. Queue persistence depends on retaining `.studio/` on disk.

Live image generation and review have now been tested. See [generation QA](generation-qa.md) for exact evidence and costs. Token-based estimates are not invoices; billing is authoritative. Large custom image dimensions are supported but experimental above the documentation's usual range; physical print quality still needs proofing.

Official references: [image generation](https://developers.openai.com/api/docs/guides/image-generation), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [image inputs](https://developers.openai.com/api/docs/guides/images-vision), [pricing](https://developers.openai.com/api/docs/pricing).
