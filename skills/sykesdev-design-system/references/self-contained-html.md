# Self-contained HTML documents

Load for any artifact that has to travel: a design brief, a status chart, a
review, a spec, a proposal. The deliverable is **one `.html` file** that opens
correctly from an email attachment, a chat upload, or a USB stick — no network,
no sibling files, no server. Authoring source and `render_check.py` PNGs are
scaffolding. They are not part of the document.

## The contract

A document is self-contained only when all of the following hold.

| Requirement | Why |
| --- | --- |
| Zero external references | The recipient has your one file and nothing else |
| Fonts embedded as `woff2` data URIs | No Google Fonts, no CDN, no fallback to Helvetica |
| Images embedded as data URIs | Including the mark; a broken mark reads as a broken document |
| CSS and JS inline | A `<link>` or `<script src>` to a sibling is a blank page |
| Works from `file://` | No fetch, no module imports, no service worker |
| Degrades without JS | Content is in the markup; JS adds behavior, never the text |

## Author multi-file, ship single-file

Do not hand-write a document with a 200 KB base64 blob in it. Author against
the shipped layers in a throwaway path, then fold it onto the destination:

```text
$TMPDIR/harbor-doc.html          authored: <link>, <script src>, <img src>
  ├── assets/tokens.css          tokens + @font-face
  ├── assets/harbor-ui.css       component layer
  ├── assets/harbor-ui.js        behavior layer
  └── assets/logos/logo-256.png
            │
            │  scripts/bundle_html.py
            ▼
dest/brief.html                  the only file that remains
```

```bash
python3 scripts/bundle_html.py "$TMPDIR/harbor-doc.html" -o dest/brief.html \
  --fonts overpass/400,overpass/600,overpass/700,overpass/800,overpass-mono/500
rm "$TMPDIR/harbor-doc.html"
```

If the user named a folder, put one `.html` in it. Do not create
`source.html`, `shots/`, or a second unbundled file beside the bundle. A
leftover source file is the one someone opens first, and from `file://` its
CSS, fonts, and mark are gone.

## What lands on disk

| Keep | Discard after use |
| --- | --- |
| The bundled `.html` at the path they named | Authored source (`<link>` / `<script src>`) |
| | `render_check.py` PNGs (tmp, for your eyes) |
| | Extra folders created only to hold scaffolding |

`render_check.py` exists so you judge the chart before handing it over. It is
not a second copy of the document. Write shots under `$TMPDIR`, look at them,
delete them.

The bundler inlines stylesheets and scripts, rewrites every local `url()`,
`src`, and `href` into a data URI, resolves `@import` recursively, drops
now-pointless `<link rel="preload">`, and then verifies its own output. It is
offline by design: a remote `https://` reference is reported as a violation,
never fetched.

Verify any document — including one you did not build:

```bash
python3 scripts/bundle_html.py --check dest/brief.html
```

## Weight

Fonts and the mark dominate. Budget deliberately.

| Asset | On disk | Inlined (base64) |
| --- | --- | --- |
| One Overpass face | ~16 KB | ~22 KB |
| `logo-256.png` | 56 KB | 76 KB |
| `logo.png` (1254px master) | 838 KB | 1.1 MB |
| Typical five-face document | — | **~225 KB total** |

- Pass `--fonts` with only the weights the document actually sets. Five faces is
  a normal document; nine is waste.
- Embed `logo-256.png`, never the master. The master is for print and large
  raster work.
- Reference each asset once. The bundler warns on a repeat because a second
  reference means a second copy of the bytes. For a tab icon, put `data-favicon`
  on the masthead `<img>` and let the behavior layer point the icon at bytes
  already in the file, rather than adding a `<link rel="icon">`.
- `--fonts none` when a document deliberately rides on system fonts (a plain
  memo). Sentence-case Overpass is the default; drop it knowingly.

## Behavior that survives a single file

`assets/harbor-ui.js` is declarative — a document opts into each behavior with a
data attribute, so it only pays for what it marks up:

| Attribute | Behavior |
| --- | --- |
| `[data-toc="main h2"]` | Build a rail from headings, with scrollspy |
| `[data-anchors="main h2, main h3"]` | Add `#` handles to those headings |
| `[data-tabs]` | Tablist with arrow-key roving focus |
| `[data-sort-table]` | Sortable headers; numeric columns sort numerically |
| `[data-filter="tableId"]` | Filter rows from a search input |
| `[data-copy="targetId"]` | Copy text, with a toast confirmation |
| `[data-dialog="dialogId"]` | Open a native `<dialog>`; `[data-close]` closes |
| `[data-toast="message"]` | Raise a toast |
| `[data-sample]` | Broadcast the trigger's `data-*` into `[data-sample-slot]` |
| `[data-favicon]` | Reuse that image as the tab icon |

Constraints that keep it working offline:

- No `fetch`, no ES module imports, no CDN. One IIFE, one `window.harbor.toast`.
- The clipboard is blocked on `file://` in some browsers, so `[data-copy]`
  falls back to selecting the text and says so in the toast.
- Interactive state lives in ARIA attributes (`aria-selected`, `aria-sort`,
  `aria-pressed`, `aria-current`), so the styling and the accessibility tree
  cannot drift apart.

## Print

`@media print` in the component layer keeps the night ground with
`print-color-adjust: exact`, hides the rail, toasts, copy buttons, and anchor
handles, expands every hidden tab panel so nothing is lost on paper, and prints
external URLs after their link text. The chart does not become a light document
when printed — there is no light theme to fall back to.

## Checklist

- [ ] Authored against `tokens.css` + `harbor-ui.css`; no re-declared hex or sizes
- [ ] `--fonts` limited to the weights actually used
- [ ] `logo-256.png` embedded, referenced once, on a dark ground
- [ ] `bundle_html.py` exits 0 with no `external` findings
- [ ] No `<a>` pointing at a sibling file — in-document `#anchors` instead
- [ ] Looked at via `render_check.py` into tmp; shots not left next to the document
- [ ] Authored source deleted; destination is the bundled file only
- [ ] Readable with JS disabled
- [ ] Reduced-motion and print checked if the document ships to reviewers
