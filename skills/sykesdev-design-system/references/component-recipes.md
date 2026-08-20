# Component recipes

The component layer ships as `../assets/harbor-ui.css` (+ `../assets/harbor-ui.js`
for behavior). It re-declares no value: every color, size, and easing comes
from `../assets/tokens.css`. Load tokens first, then the layer.

This file gives the **markup shape and the rules** for each component, because
those are what CSS cannot tell you. Do not paste the CSS from here into a page —
link the layer, or port it into the target stack's component files.

Live plates: `../assets/previews/components.html` (states) and
`../templates/document.html` (a document skeleton).

## Shared law

- Square. Radius 0 on plates, buttons, chips, inputs, dialogs.
- Hairline `--rule` before any shadow. Shadows only for floating UI (dialog, toast).
- Keyboard focus is 2px lamp at 2px offset, never the browser default ring.
- Disabled: `--plate` fill, `--lamp` text, diagonal ink hatch, `disabled` or
  `aria-disabled` — never color alone.
- Error: dashed `--lamp` rule, the word `error`, and the recovery. No red exists.
- Status is a mark plus a word. Never a hue this system does not own.
- Interactive state lives in ARIA attributes; the CSS keys off them
  (`aria-selected`, `aria-sort`, `aria-pressed`, `aria-current`, `data-error`).
- Sentence case everywhere. No uppercase tracked labels or CTAs.

## Layout

| Class | Job |
| --- | --- |
| `.shell` | Page grid: masthead spanning, then rail + sheet. 20px ink gaps. |
| `.masthead` | Mark, title, mono meta block. The mark goes on dark only. |
| `.sheet` | The main column: a stack of plates, 20px apart. |
| `.plate` | A chart plate: `--plate` ground, 1px rule, 24px padding. |
| `.plate-grid` | Auto-fit columns inside one plate. |
| `.well` | Recessed `--shoal` panel for a readout inside a plate. |

Plates do not nest — a plate inside a plate is the mistake this system exists to
avoid. Use `.well` for a recess, or split into sibling plates. Do not build the
page as a grid of icon + heading + text cards.

```html
<div class="shell">
  <header class="masthead">
    <img class="mark" src="logo-256.png" width="72" height="72" alt="sykesdev mark" data-favicon>
    <h1>Title</h1>
    <p class="meta"><b>context</b>secondary line</p>
  </header>
  <nav class="rail" aria-label="Sections" data-toc="main h2"><h2>On this page</h2></nav>
  <main class="sheet" data-anchors="main h2, main h3">
    <section class="plate">…</section>
  </main>
</div>
```

## App shell and navigation

- `.rail` — sticky section rail. Populated by `[data-toc]`; the current entry
  carries `aria-current="true"` and a lamp left border. It collapses to static
  flow under 900px.
- `.crumbs` — one line, `/` separators from `::before`, last item
  `aria-current="page"`. Not a second navigation system.
- `.tabs` — real ARIA tabs: `[role=tablist]` of `[role=tab]` buttons with
  `aria-controls`, each `[role=tabpanel]` labeled by its tab. Arrow keys move
  focus and selection; `Home`/`End` jump. The selected tab is lamp text on a
  lamp bottom border. Hidden panels use the `hidden` attribute so print can
  expand them.

```html
<div class="tabs" data-tabs>
  <div role="tablist" aria-label="Recipes">
    <button role="tab" type="button" id="t-a" aria-controls="p-a" aria-selected="true">One</button>
    <button role="tab" type="button" id="t-b" aria-controls="p-b" aria-selected="false">Two</button>
  </div>
  <div role="tabpanel" id="p-a" aria-labelledby="t-a" tabindex="0">…</div>
  <div role="tabpanel" id="p-b" aria-labelledby="t-b" tabindex="0" hidden>…</div>
</div>
```

There is no sidebar app-nav pattern. A document gets the rail; an application
gets a masthead plus tabs. Do not import a generic docs-site sidebar.

## Buttons

`.btn` plus one of `.btn-primary` (lamp plate, ink text, 10.9:1),
`.btn-secondary` (lamp rule on ink), `.btn-ghost` (lamp text, rule on hover).
`.btn-small` is the mono utility size for in-plate actions such as copy.
Group with `.btn-row`; add `.actions` to push a row right, primary last.

One primary action per plate. Hover shifts lamp to foam, press to mist.

## Forms

`.field` is a labeled column: `label`, control, then `.hint` or `.error`.
Controls sit on `--ink` — the input is a tide-table cell cut into the plate.
Placeholders are `--buoy` (9.4:1), never a faint gray.

- `form.stack` stacks fields 16px apart.
- `.field[data-error]` switches the control to a dashed lamp rule; pair it with
  `aria-invalid="true"` and `aria-describedby` pointing at the `.error`.
- `.check` is the square check control; the tick is ink on lamp.
- An error summary belongs at the top of a long form, same dashed-lamp rule.

Error copy names the problem and the fix:
`error — white is not a named token. Use paper, lamp, buoy, or ink.`

## Data

- `table.table` — hairline row rules, sticky `--shoal` header, hover row on
  `--shoal`, `.num` cells right-aligned in Overpass Mono with tabular figures.
  Add `data-sort-table` and the behavior layer turns each header into a sort
  button carrying `aria-sort`; mark a column `data-no-sort` to opt out. Give
  the table an id and point a search input at it with `data-filter="thatId"`.
  Wrap in `.table-wrap` so narrow viewports scroll the table, not the page.
- `dl.kv` — mono key/value readout. `dt` is lamp, `dd` is buoy. This is the
  shape for metadata, contrast pairs, and provenance.
- `.stat` — one big mono `.value` over a quiet `.label`. Not a dashboard tile.
- `.meter` — 8px rule with a lamp fill span; give it
  `role="img"` and an `aria-label` carrying the number.
- `.code` — `--ink` well with a mono `pre` and an absolutely positioned
  `.btn-small`. Wire copying with `data-copy="preId"`; inline `code` gets a
  hairline rule so it reads as a chart cell.
- `.chip` — mono sounding tag with a rule; `data-sampled="true"` turns the rule
  lamp. Not a pill, never a filled badge.

## Overlays and feedback

- `dialog.plate-dialog` — native `<dialog>`, lamp rule, offset shadow, ink
  backdrop at 78%. Open with `data-dialog="id"`, close with `[data-close]`.
  Native modality gives focus trapping and `Escape` for free.
- `.toast` / `.toast-stack` — bottom-right stack, lamp left border, offset
  shadow, auto-removed. The stack is `role="status"` + `aria-live="polite"`.
  Raise one with `data-toast="message"` or `window.harbor.toast(message)`.
- `.tip` — a dashed-underline trigger wrapping a `.tip-body` tooltip shown on
  hover and focus-within. The trigger needs `tabindex="0"` and
  `aria-describedby`; the body is `role="tooltip"`. Never put an action in it.
- `.callout` — bordered note with a mono `.label`. Default is quiet kelp;
  `data-kind="signal"` goes lamp; `data-kind="warn"` goes dashed lamp. The label
  word carries the status.
- `.empty` — dashed rule, `.title`, one sentence saying what to do. An empty
  state names the next action; it does not apologize.
- `.loading` — a lamp tick sweeping a 2px rule. No spinner. Under
  `prefers-reduced-motion` it holds still.

## Document furniture

- `[data-toc]` on `.rail` builds the table of contents; `[data-tocLabel]` (as
  `data-toc-label`) overrides a long heading.
- `[data-anchors]` appends `.anchor` handles that appear on hover or keyboard
  focus. Heading ids are slugged from the heading's own words.
- `.footnotes` — top rule, ordered list, `sup > a` references. A targeted
  footnote gets a lamp outline so the jump is visible.
- `.visually-hidden` for table captions and headings that structure but do not
  show.
- `@media print` keeps the ground, drops the furniture, expands tab panels.

## Motion

One authored moment per surface. Default is `.graticule`: a west-to-east lamp
wipe, 600ms, that uncovers the grid of already-visible content. Hover 120ms,
press 80ms, focus instant. Under `prefers-reduced-motion: reduce` the wipe, the
toast rise, and the loading sweep all stop and transitions collapse to 1ms.
