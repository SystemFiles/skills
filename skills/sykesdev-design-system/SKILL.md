---
name: sykesdev-design-system
description: Applies the sykesdev Harbor Chart design system to build application UI, static pages, and fully self-contained single-file HTML documents (briefs, status charts, reviews) that open correctly with no network or sibling files. Use when designing or polishing an interface, choosing tokens/type/spacing/components, placing the logo, generating a shareable HTML artifact, or auditing work against this system.
---

# sykesdev-design-system

Night harbor chart. Tokens are soundings, components are buoys, type and space
are the tide table. Local files are the only source — no CDN, no Google Fonts,
no network at runtime or build time.

## When to use

- Designing or implementing application UI: dashboards, tools, forms, tables.
- Producing a **self-contained HTML document** to send someone: one file, opens
  from mail or `file://`, everything embedded.
- Static pages and sites that should look like sykesdev.
- Token, type, spacing, component, or logo decisions.
- Auditing existing work against this system.

## Core facts

Hold on every surface. Load references for the rest.

- Canvas is night-channel `--ink` `#0B1018`. The field is water, not a card on gray.
- Paper `#E6EDF5` is body text on ink (16.2:1). Buoy `#A7B8CC` is secondary (9.4:1). Lamp `#05DBCC` is the signal — the mark’s cyan — primary fill, focus, sampled — not body copy.
- Elevation: plate `#141C28`, shoal `#1A2433`, rule `#3A4A5E`. Fathom `#243044` is structure, never type.
- Overpass for labels and body. Overpass Mono for soundings, hex, token names, and measurements.
- Logo `assets/logos/logo.png` on dark grounds only, `logo-256.png` for screens and embedding. No reverse exists — do not invent one.
- Hairline graticule before shadows. Plates are square, never nested. Gaps between plates are ink, 20px.
- One theme, and it is dark. No light mode, no sixth hue, no radius, no red.
- Contrast floors: 4.5:1 body, 3:1 large text and non-text UI. No a11y standard is committed beyond that floor.

## The three layers

Never re-declare a value that a layer already owns.

```text
assets/tokens.css      color, type, space, motion, @font-face   ← load first
assets/harbor-ui.css   components: shell, plates, controls,      ← link or port
                       tables, tabs, dialogs, toasts, callouts
assets/harbor-ui.js    behavior, opted into with data-*          ← link or port
```

## Task routing

- **document** — the user asked for a document, so leave **one bundled `.html`**
  at the path they named. Not a folder of source + bundle + screenshots: the
  unbundled sibling is a broken `file://` page, and it is what people open
  first. Load `references/self-contained-html.md` and
  `references/component-recipes.md`. Copy `templates/document.html` into
  `$TMPDIR`, replace the content, bundle onto the destination:

  ```bash
  python3 scripts/bundle_html.py "$TMPDIR/harbor-doc.html" -o dest/doc.html \
    --fonts overpass/400,overpass/600,overpass/700,overpass/800,overpass-mono/500
  ```

  Gate: exit 0, no `external` findings. Judge with `render_check.py` (it writes
  PNGs under tmp). Delete the authored source after the bundle succeeds. Do not
  keep `source.html`, `shots/`, or an unbundled sibling next to the deliverable.

- **implementation** — app UI or a site. Load `references/harbor-chart.md`,
  `references/component-recipes.md`, `references/asset-index.md`. Take
  `tokens.css` verbatim; implement the component contracts in the target stack.
  Do not import these HTML previews as a component library.

- **audit** — use the contract below. Cite files checked. Prove contrast, type,
  logo ground, and palette closure. Render the artifact rather than asserting
  from source.

## Audit contract

```markdown
## Chart audit

- Scope: [files / surfaces]
- On-chart: [what matches]
- Off-sounding: [mismatches with the reference that proves it]
- Fixes: [exact token, type, asset substitutions]
- Verification: [contrast pairs, logo ground, paper-on-ink body, self-containment check, screenshot]
- Sources: [local files read; live verification N/A]
```

## Workflow

- [ ] Mode: document, implementation, or audit.
- [ ] Load only the references that mode needs.
- [ ] Canvas ink. Body paper. Lamp for action and focus. Tokens from `assets/tokens.css` only.
- [ ] Components from `assets/harbor-ui.css` — link it, or port the contracts. Never re-declare its values.
- [ ] Overpass / Overpass Mono from `assets/fonts/`, not a CDN.
- [ ] Logo on dark only; `logo-256.png` when embedded; omit it rather than place it on light.
- [ ] Interactive state in ARIA attributes, not classes alone.
- [ ] Documents: one bundled file at the destination; `--check` clean; no sibling source, shots, or links; readable with JS off.
- [ ] Reduced motion and print pass before sending an artifact to a human.
- [ ] No invented logo variant, no sixth hue, no light theme, no Liatrio look.

## References

- `references/harbor-chart.md` — posture, tokens, type, space, motion, print, copy, porting.
- `references/component-recipes.md` — markup shape and rules for every component.
- `references/self-contained-html.md` — the single-file contract, bundling, weight budget.
- `references/asset-index.md` — every shipped file, logo and font rules.
- `assets/tokens.css`, `assets/harbor-ui.css`, `assets/harbor-ui.js` — the layers.
- `templates/document.html` — starter for a self-contained document.
- `assets/previews/index.html` — night-chart plate (human judgment + copyable field).
- `assets/previews/components.html` — component layer with states.
- `scripts/bundle_html.py` — fold a page into one file; `--check` verifies one.
- `scripts/render_check.py` — tmp screenshots so you look at the chart, then discard.
