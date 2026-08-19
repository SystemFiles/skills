# PR feedback Q&A — templates

Use these shapes in chat. Do not invent parallel formats.

## Plan mode gate

```markdown
This workflow needs **Plan mode**.

Switch to Plan mode, then reply **ready**.
I will not load feedback or start Q&A until Plan mode is on.
```

If the mode-switch tool is available, call it with target `plan` and a one-line reason, then wait.

## Session choice

```markdown
**Session**

1. New persisted session under `.scratch/pr-feedback-qa/`
2. Resume an existing session
3. Ephemeral (chat only; no file)

Reply `1`, `2`, or `3`.
```

On `2`, list matching `.scratch/pr-feedback-qa/*.json` and ask which slug.

## Item prompt

```markdown
**Issue N/M — <short title>**

<1–3 lines: what is wrong and why it matters>

**How to fix?**
1. <option>
2. <option>
3. Other (describe)

**Disposition?**
- **A)** Address
- **S)** Skip
- **I)** GitHub Issue

Reply e.g. `A1`, `S`, `I`, or a clarifying question.
```

Adapt option count. Always keep **Other (describe)**. Prefer a recommended option when the review names one; say so in one short line under the options if useful.

## After a clarifying question

Answer in plain language. Then reprint the same **How to fix?** and **Disposition?** block for the current item. Do not advance.

## Decision recorded

```markdown
**Issue N — decided: <Address (A#) | Skip | GitHub Issue>**

<one-line note: fix choice, skip reason, or preferred fix for the issue>

---

**Issue N+1/M — …**
```

## Decision summary

```markdown
**Decisions**

| # | Disposition | Notes |
| --- | --- | --- |
| 1 | Address | <fix gloss> |
| 2 | Skip | <reason or —> |
| 3 | GitHub Issue | <preferred fix; labels> |
```

Then:

```markdown
**Queued GitHub issues:** N

Create them now with `bug` / `enhancement` labels?
Reply **yes** to create, or **no** to stop after the table.
```

## GitHub issue body

```markdown
## Context
From review of <PR URL or file path> (finding #<N>).

## Problem
<short problem statement>

## Preferred fix
- <chosen or preferred option>

## Refs
- <PR URL and/or file path>
- <comment URL if any>
```
