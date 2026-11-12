# Product

## Register
product

## Users
US pet owners creating a personalized keepsake or gift, primarily on a phone or laptop.

## Product Purpose
Turn a pet photograph into minhwa-inspired artwork and choose a digital file, unframed print, or framed print. This local MVP tests the complete journey with optional OpenAI image generation, artwork approval, and simulated purchases. API generation uses credits; real payments and fulfillment are not implemented.

## Brand Personality
Personal, considered, artful. Derive the artwork direction from the supplied peony and lotus references.

## Anti-references
Generic breed portraits, cartoon simplification, pasted photographic cutouts, and technical generation settings in the customer flow.

## Design Principles
- Let the pet and artwork lead.
- Preserve recognizable identity and the approved artwork.
- Make each next step and its consequences clear.
- Keep samples and test transactions unmistakable.

## Accessibility and Inclusion
Labeled inputs, keyboard operation, readable contrast, mobile upload support, announced status, and reduced motion, as required by the product spec.

## Implemented local generation
One customer photo first produces a private, undecorated, QA-gated identity study. When every internal likeness and material criterion passes, the study plus five references from the selected peony-and-butterfly, lotus-and-butterfly, or pine-and-magpie garden drive a fresh whole-canvas painting automatically. Customers see only the completed garden portrait. The final is never layer-composited and must pass independent identity, material, garden-specific scale, composition, and harmony gates before owner review. Pine requires a visibly smaller pet and a substantially larger tree than the flower gardens. Flagged paintings require explicit studio review. Downloads preserve an immutable named master. Final-art corrections reuse the private identity lock. Payments and physical fulfillment remain simulated. See `docs/generation-qa.md` for validation limits.
