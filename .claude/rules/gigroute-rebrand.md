# GigRoute Rebrand Rules

## Naming

Replace ALL occurrences of:
- "Live Tour Manager" → "GigRoute"
- "Tour Manager" (as product name) → "GigRoute"
- "Studio Palenque Tour" → "GigRoute"
- "tourmanager" (in identifiers) → "gigroute"
- "tour-manager" (in URLs/slugs) → "gigroute"

Keep "tour manager" (lowercase, as role description) — it describes the person, not the product.

## Color Palette (CSS Variables)

```css
:root {
  --gr-black: #0F0F14;
  --gr-amber: #FFB72D;
  --gr-white: #FAF8F5;
  --gr-amber-soft: #FFD278;
  --gr-surface: #191920;
  --gr-success: #34D399;
  --gr-warning: #FB923C;
  --gr-error: #F87171;
  --gr-draft: #6B7280;
}
```

## Typography

- Titles/Logo: `font-family: 'Outfit', sans-serif; font-weight: 700;`
- Body UI: `font-family: 'Inter', 'Instrument Sans', sans-serif; font-weight: 400;`
- Data/Code: `font-family: 'Geist Mono', 'JetBrains Mono', monospace; font-weight: 400;`

## Assets Location

Brand assets are in the parent directory (`../`):
- `gigroute-icon-512.png` — App icon
- `gigroute-logo-dark.png` — Horizontal logo (dark bg)
- `gigroute-logo-light.png` — Horizontal logo (light bg)
- `gigroute-wordmark-dark.png` — Wordmark (dark bg)
- `gigroute-social-card.png` — Open Graph card

These must be copied to `app/static/img/` during rebrand.

## Meta Tags

```html
<title>GigRoute — Du bureau au backstage</title>
<meta name="description" content="L'outil de gestion de tournees concu pour les musiques actuelles">
<meta property="og:title" content="GigRoute">
<meta property="og:description" content="Vos tournees. Simplifiees.">
<meta property="og:image" content="/static/img/gigroute-social-card.png">
```

## Email Sender

Update `MAIL_DEFAULT_SENDER` from `noreply@tourmanager.app` to `noreply@gigroute.app`
