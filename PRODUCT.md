# Product

## Register
product

## Users
US pet owners creating a personalized keepsake or gift, primarily on a phone or laptop.

## Product Purpose
Turn two complementary pet photographs into minhwa-inspired artwork and choose a digital file, unframed print, or framed print. This local MVP tests the complete journey with optional OpenAI image generation, artwork approval, and simulated purchases. API generation uses credits; real payments and fulfillment are not implemented.

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
Face photo plus full-body photo and four style anchors; one fresh painting per attempt; joint photo validation, automated art review and release when all checks pass, then owner approval. The face photo governs facial geometry and expression while the body photo governs silhouette, proportions, coat and markings. Flagged paintings require explicit studio review. Downloads preserve an immutable named master. Corrections retain both identity references. Payments and physical fulfillment remain simulated. See `docs/generation-qa.md` for validation limits.
