# Asset index

Everything the system ships. Paths are relative to this file.

| File | Job |
| --- | --- |
| `../assets/tokens.css` | Tokens, base element styles, `@font-face` rules. Load first. |
| `../assets/harbor-ui.css` | Component layer. Values come from tokens only. |
| `../assets/harbor-ui.js` | Behavior layer, opted into with `data-*` attributes. |
| `../assets/fonts/*.woff2` | Overpass 400–800, Overpass Mono 400–700. |
| `../assets/logos/logo.png` | Mark master, 1254×1254. Print and large raster. |
| `../assets/logos/logo-256.png` | Mark for screens and for embedding. |
| `../templates/document.html` | Starter for a self-contained document. |
| `../assets/previews/index.html` | Night-chart plate: soundings, tide legend, live sample. |
| `../assets/previews/components.html` | Component layer with states. |
| `../scripts/bundle_html.py` | Fold a page into one self-contained file; verify one. |
| `../scripts/render_check.py` | Tmp screenshots so a chart can be judged, then discarded. |

The previews and the template are plates to judge and copy. They are not a
component library to import — the library is `harbor-ui.css`.

## Logo

Geometric S in four corner brackets, cyan on black. 8-bit RGB, **no alpha**:
the file is a black square, not a knockout.

| File | Pixels | Bytes | Use |
| --- | --- | --- | --- |
| `logo.png` | 1254×1254 | 838 KB | Master. Print, large raster, source for derivatives. |
| `logo-256.png` | 256×256 | 56 KB | Screens, favicons, anything embedded. |

Rules:

- Dark grounds only (`--ink`, `--plate`, `--shoal`). On a light ground the black
  field becomes a visible box.
- Do not recolor, rotate, add a drop shadow, or place it on lamp/buoy/kelp fills.
- Do not invent a reverse, a wordmark, or a transparent cutout. If the ground is
  light, omit the mark.
- Clear space: one corner-bracket width on every side; at least 16px.
- Alt text: `sykesdev mark` when informative; `alt=""` when it sits beside a
  visible `sykesdev` heading.
- Embed `logo-256.png`, never the master — the master costs 1.1 MB as base64.
  New sizes are downscales of the master (`sips -Z 256 logo.png --out …`), not
  redraws.

Favicon: no second file and no `<link rel="icon">` in a document you intend to
bundle. Put `data-favicon` on the masthead `<img>` and the behavior layer points
the tab icon at bytes the file already carries.

## Fonts

Self-hosted, one weight per file, latin subset.

| Family | Weights | Job |
| --- | --- | --- |
| Overpass | 400, 500, 600, 700, 800 | Everything people read |
| Overpass Mono | 400, 500, 600, 700 | Soundings, hex, token names, measurements, code |

Never call Google Fonts or any CDN — not in an app, not in a document. The
`@font-face` rules in `tokens.css` point at `fonts/*.woff2` relative to that
file, so the stylesheet keeps working when it is copied or bundled.

When bundling, pass `--fonts` with only the weights the document uses; each
inlined face costs about 22 KB. A five-face document is normal.
