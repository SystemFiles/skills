# SDD Q&A — formats

## Question file shape

Each question block in `NN-questions-*-….md`:

```markdown
## N. Short title

Context paragraph(s). Stem question?

- [ ] (A) Option text
- [ ] (B) Option text
- [ ] (C) Other (describe)

**Recommended answer(s):** [(A) or (B)]

**Why these are recommended:**

- Bullet why.
```

After the user answers, mark choice(s) with `[x]` and insert **above** Recommended:

```markdown
- [x] (A) Option text
- [ ] (B) Option text

**Decision:** (A)

**Additional context:** <notes, or `None.`>
```

If they pick a combo (e.g. A+D), check all relevant boxes; Decision line states the combo.

## Asking (chat) — one question only

```markdown
**QN — Short title**

<1–3 lines of stem / stakes>

- **(A)** …
- **(B)** …
- **(C)** …

**Recommended:** <letter(s)> — <one-line why>

Pick + any context.
```

Do not dump later questions. Keep options scannable (bold letter, short text).

## After they answer

1. Edit the questions file (checkbox + Decision + Additional context).
2. Confirm, then ask the next:

```markdown
**QN recorded:** (X) — <optional one-line context>

---

**Q{N+1} — Short title**
…
```

## Clarifications mid-question

Answer plainly. Stay on the same Q until they pick a letter (or Other). Then record.

## Done — decision summary

```markdown
Round complete. Written to `<path>`.

| # | Decision |
|---|---|
| 1 | (A) short gloss |
| 2 | (B) short gloss |
```
