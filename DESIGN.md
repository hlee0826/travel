# Minhwa Studio design

## Direction

An approachable portrait shop with the quiet visual presence of a Korean painting studio. Pet owners browse at home on a phone or laptop; artwork and clearly labeled choices should make a personal gift easy to imagine.

The user selected two references on November 5, 2026:

- [But Poorly Drawn](https://butpoorlydrawn.com/): three illustrated purchase formats, ordered process, inline product configurator, FAQ and closing call to action.
- [이선구 민화공방](https://www.xn--lg3bu59b.kr/): ivory backgrounds, cinnabar actions, dark warm text, traditional serif headings, generous painting displays and restrained gallery captions.

Use those principles with our own copy and existing sample artwork. Do not copy the reference sites' art, identity, reviews or business claims. UI/UX Pro Max's generic Swiss/Art Deco suggestions were a poor fit; the user-selected references take precedence.

## Palette and typography

The CSS variables in `hosted_web/styles.css` are authoritative. Ivory #f7f3e9, light mineral #eee8da, ink #302e29, muted text #686052, cinnabar #a6372b, pale red selection #f4e6db, soft moss #e5e8dd. Paper-like backgrounds are an explicit reference choice, not a generic default.

Georgia for display headings; system sans for forms, navigation, prices and body text. Warm red pill actions, square artwork displays, thin rules, compact 4px corners on form controls. Interface typography needs no external font service. Download masters use bundled OFL-licensed Noto Serif KR for English and Hangul names.

## Layout and behavior

- Home: full-width Japandi room photograph with white headline, one supporting sentence and one action → three formats → three-step process → live sample configurator → two gardens → FAQ → final action.
- Configurator selects composition, format and physical size; its link carries those choices to upload and subsequent product selection.
- Upload, review, checkout and order screens share the storefront palette. Desktop uses artwork alongside controls; mobile stacks them.
- The mobile menu uses an expanded state, closes after navigation and supports Escape. Native inputs and FAQ disclosures remain keyboard accessible.
- Image hover effects are short and finite; content remains available without animation. Reduced motion removes animation and transitions. No continuous decorative movement in the creation flow.
- Gallery image crops are decorative. Approval uses a saved preview; new downloads use the immutable named master. A 12 × 16 mat adds paper above and below without cropping the 4:5 painting.

## Product truth

This remains a local MVP, not a live store. All prices are examples; checkout is simulated; nothing is charged or shipped. Samples are explicitly labeled. OpenAI generation now runs automatically for newly consented uploads; legacy manual handoffs remain supported. Source isolation, approvals and downloads remain in place. API credit use is disclosed on the upload screen. Do not publish the local Python server.

## Homepage hero photography

The hero uses `hosted_web/assets/hero-options/hero-02-reading-nook-dog.png`: the selected Japandi reading nook with the user’s generated dog portrait in a natural oak frame. Desktop text sits on the shaded left; narrow screens place text below the painting with a bottom gradient. Prompt and provenance: `docs/reading-nook-dog-hero.md`.
