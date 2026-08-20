# Harbor Chart

Load for implementation that needs more than the core facts in `../SKILL.md`. Values live in `../assets/tokens.css`. Import that file; do not retype hex except in artifacts that cannot include CSS.

The system applies to three kinds of surface, with the same posture in each:

| Surface | Layers to use |
| --- | --- |
| Self-contained HTML document | `tokens.css` + `harbor-ui.css` + `harbor-ui.js`, then `scripts/bundle_html.py` |
| Application UI (web, dashboard, tool) | Port tokens + component contracts into the target stack |
| Static site or page | Link the layers directly |

## Posture

The surface is a night chart on a table. Ink `#0B1018` is the channel. Type is paper, not the accent. Lamp `#05DBCC` is the signal — the mark’s cyan — sampled soundings, primary fill, focus. No cream, no all-teal body, no generic design-system sidebar.

- One field of water. Plates float in it with 20px ink gaps.
- Graticule: hairline `--rule` lines before any shadow.
- Shadows are for floating UI only (menus). Offset + blur; no glow halo as depth.
- Square corners. Chart plates are cut rectangles, not pills.

## Color

| Token | Hex | Job |
| --- | --- | --- |
| `--ink` | `#0B1018` | Canvas, gaps, on-lamp text |
| `--plate` | `#141C28` | Elevated plate |
| `--shoal` | `#1A2433` | Recessed well |
| `--fathom` | `#243044` | Deep structure, never text |
| `--rule` | `#3A4A5E` | Graticule and borders |
| `--paper` | `#E6EDF5` | Body and titles (16.2:1 on ink) |
| `--buoy` | `#A7B8CC` | Secondary text, placeholders, ticks |
| `--kelp` | `#7E92A8` | Quiet labels, scrollbar |
| `--lamp` | `#05DBCC` | Signal: mark cyan, primary fill, focus, sampled |
| `--foam` | `#54E1DA` | Primary hover (lamp + paper) |
| `--mist` | `#079E96` | Primary press (lamp + ink) |

Paper is a chart token, not “white.” Do not use `#FFFFFF`. Status is a mark plus a word, not a red you do not have.

Contrast (body ≥4.5, large ≥3):

- paper on ink 16.2; buoy on ink 9.4; kelp on ink 6.0; lamp on ink 10.9
- ink on lamp 10.9; ink on foam 12.0; ink on mist 5.8
- fathom is structure only

## Type

Overpass for everything people read. Overpass Mono for soundings, hex, token names, measurements, code.

| Role | Size | Weight | Face |
| --- | --- | --- | --- |
| Chart title | 40px (max 2.5rem) | 800 | Overpass, tracking -0.02em |
| Plate title | 24px | 700 | Overpass |
| Body | 16px, 65–75ch | 400 | Overpass |
| Control | 15px | 600 | Overpass |
| Sounding | 12–14px | 500 | Overpass Mono, tabular |

Sentence case. No uppercase tracked eyebrows — the heading is the heading. Mono is for data, not costume.

Self-host `../assets/fonts/*.woff2`. Do not call Google Fonts.

Long-form documents get the same type: body 16px at a 70ch measure, `h2` at
24px/700 with more space above than below, `h3` at 20px/700. Mono is data, not
costume — a heading never goes mono to look technical.

## Space, grid, radius

- Scale: 4, 8, 12, 16, 24, 32, 48, 64. More space above a heading than below it.
- Plate gap: 20px of canvas.
- Radius: 0 on plates, buttons, chips, inputs. The chart is cut square.
- Content width: chart can go full viewport; reading measure 70ch.

## Motion

One authored moment per surface. Default: a west-to-east lamp wipe that reveals the graticule (`clip-path` or mask), 600ms `--ease`. Already-visible content; the wipe uncovers the grid, it does not fade the page in.

- Hover: 120ms, lamp elements shift to foam or gain a 1px rule; no bounce.
- Press: 80ms, background mist.
- Focus: 2px lamp outline, 2px offset. Never the browser ring.
- `prefers-reduced-motion: reduce` — no wipe, instant state.

## Copy

Owner voice, low fluff, sentence case. Controls name the action (`Sample lamp`, `Fix contrast`). Errors name the problem and the fix. No emoji. No exclamation marks in UI.

## Browser chrome

Theme selection (`lamp` fill, `ink` type), caret (`lamp`), scrollbars (`kelp` on `ink`), focus as above, tabular lining figures on all soundings.

## Print

There is one theme and it is dark, so print keeps the ink ground with
`print-color-adjust: exact` rather than inventing a light reverse. The rail,
toasts, copy buttons, and anchor handles are hidden; hidden tab panels expand so
paper loses nothing; external URLs print after their link text. If a printed
artifact must be light, it is not this system — say so instead of bleaching it.

## Porting to an application

Take `tokens.css` verbatim as the token layer. Take the component contracts from
`component-recipes.md` and implement them in the target stack's own component
files — the class names in `harbor-ui.css` are a reference implementation for
plain HTML, not an API to shim. Keep the ARIA-attribute-driven state model:
`aria-selected`, `aria-sort`, `aria-pressed`, `aria-current`, `data-error`.
Never introduce a sixth hue, a radius, a light theme, or a second font family
to satisfy a framework's defaults.
