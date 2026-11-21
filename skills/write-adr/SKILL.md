---
name: write-adr
description: Use when the user wants to record, draft, supersede, or review an architecture decision record (ADR) in this repo, or says "write an ADR" or "we decided".
---

# Write an ADR

ADRs live in `docs/adr/` and use the MADR template at
`docs/adr/templates/adr-template.md`. Read `docs/adr/README.md` for the rules
and the index.

## Steps

1. **Understand the decision.** Ask what problem it solves, what constraints
   apply, and whether it is decided or still open. Ask 1-2 questions at a time.
2. **Pick a research mode.** Offer:
   - open research: find 3-5 serious alternatives, or
   - guided research: dig into the user's alternatives and add 1-2 more.
3. **Research.** Use current primary sources (docs, release notes, issues).
   Don't rely on memory alone; versions and features change.
4. **Draft.** Copy the template to `docs/adr/NNNN-kebab-title.md`, where
   `NNNN` is the next unused number. Front matter: `status: proposed`, today's
   `date`, `decision-makers` (ask). If undecided, write the Decision Outcome
   as "TBD, pending review".
5. **Review with the user** section by section: context, missing or irrelevant
   options, pros and cons, outcome. Revise.
6. **Finalize.** Set the status, add a row to the index in
   `docs/adr/README.md`, then commit with jj:
   `jj describe -m "docs(adr): NNNN <title>"`. Open a PR with the `github-pr`
   skill and `.github/PULL_REQUEST_TEMPLATE.md`, bookmark `adr/NNNN-short-title`.

## Rules

- One decision per ADR. Split topics that bundle several.
- Never edit an accepted ADR. Supersede it with a new one and set the old
  status to `superseded by ADR-NNNN`.
- Ground every pro and con in a documented behavior or real experience. Say
  when you're unsure.
- Keep it to 1-2 pages. Bullets over paragraphs.
- Use the template. Don't invent sections.
