---
name: eli5-concrete
description: >-
  Explain a topic like I'm five, as an HTML page of big pictures and few words,
  with each picture grounded by a concrete example: the real code, config, file
  tree, command or error message it stands for, shown as a before → after delta
  when something changes. Use when the user types /eli5-concrete <topic>, asks
  for an eli5 "with examples", "with code", "with config", or "grounded", or
  says the plain pictures alone do not give them a mental model they can map
  onto the real files. Works for MRs, PRs, plans, specs, codebases and
  concepts.
argument-hint: "<topic | MR/PR URL | plan file | path>"
---

# eli5-concrete

Builds on [`eli5`](https://github.com/anthropics/claude-plugins-community/tree/main/eli5)
(Apache-2.0). `eli5` gives a picture. This skill puts the real artifact under it,
so the reader can check the picture against the code they will actually touch.

Topic: $ARGUMENTS

## The page, panel by panel

One panel per idea. Each panel has three layers, in this order:

1. **Picture.** A big inline SVG, made of shapes and emoji, carrying one idea. It
   needs only a few words, and a title the reader could repeat to someone else.
2. **One sentence.** Plain words, no jargon. Name the real thing (field, file,
   command) in `<code>` once, so the picture is tied to its name.
3. **Concrete example.** The smallest real snippet that shows the idea: a few
   lines of YAML, a function signature, a file tree, a CLI call and its output,
   or an error message. When the idea is a change, show **before** and
   **after** side by side, with the lines that changed coloured.

A panel with no concrete example needs a reason: a pure "not decided yet" list
or a summary. Every other panel gets one.

## Gather the source first

Never explain from memory. Read the real thing before drawing:

- **MR or PR URL:** `glab mr view` / `gh pr view` for the description, then the
  changed files themselves (`glab api …/repository/files/<path>/raw?ref=<branch>`,
  `gh pr diff`). A plan's MR usually carries the plan as a file: read the file,
  not just the description.
- **Plan, spec or doc:** read it whole. Note each decision's status (decided,
  proposed, open) and show it as a tag on the panel.
- **Code:** read the files that implement the idea. Use the real names.
- **Concept with no codebase:** use a tiny, runnable example, and label it as
  illustrative.

## Rules for the examples

- **Copy, don't invent.** Lift snippets verbatim from the source, trimmed with
  `…`. When the source describes something but doesn't show it (often the
  "before" state), rebuild it from the description and caption it `(simplified)`.
- **The examples must obey the rules they illustrate.** Before writing each
  snippet, check it against every rule the page explains, not just its own
  panel's. A "valid" example that breaks the rule from three panels back teaches
  the wrong model.
- **Use one running example.** Use the same team, service and file names in
  every panel, so the reader builds one picture rather than five.
- **Show the delta, not the whole file.** Keep each snippet to 15 lines or
  fewer. Colour removed or failing lines red and added or valid lines green. Grey
  comments say which picture element a line maps to, such as `# 🧸 the mock`.
- **Show the failure.** When a rule rejects something, show the bad input and the
  real error message, if the source has one.
- **Caption every snippet** with its file path or the role it plays ("Owner:
  service.yaml", "Consumer: e2e.environment.yaml").

## Build it

Start from [`references/template.html`](references/template.html). It has the
styles, a before → after code grid, and one example panel. Keep the page
self-contained: inline CSS and SVG, no network.

- Write the page outside any repo, such as `/tmp/eli5-<slug>.html`, unless the
  user names a place. Open it with `open <file>`.
- Add a top nav of numbered pills, one per panel.
- Mark later or unsettled parts visibly (a dashed panel, a "proposed" tag).
- The footer names the sources the page was built from.

## Check it before reporting

Look at the page. Don't assume it renders. A headless screenshot is enough:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
  --disable-gpu --hide-scrollbars --window-size=1300,10000 \
  --screenshot=/tmp/eli5-check.png "file:///tmp/eli5-<slug>.html"
sips --cropToHeightWidth 1300 1300 --cropOffset <y> 0 /tmp/eli5-check.png \
  --out /tmp/eli5-crop.png
```

Read crops from a few panels. Fix any code block that clips horizontally: widen
the panel, shorten the line, or drop to one column.

## Report

Say where the file is, then give a short table of panel → what its example
shows. Say which examples were rebuilt rather than copied.
