---
name: useful-mr-descriptions
description: >-
  Write or rewrite merge request and pull request descriptions as a short
  TLDR blockquote, then Why, then What changed. Use when the user asks to
  write, fix, shorten, clean up, or rewrite an MR or PR description, when
  creating or updating an MR or PR, or when a description is too long, reads
  like a commit log, or buries what the reviewer needs.
---

# Useful MR descriptions

A reviewer should know what the MR does and whether they have to do anything
from the first two lines. Everything after that is for the reviewer who wants
to know why and what to look at.

Read the `write-better` skill before you draft. For GitHub mechanics
(preflight, pushing, `gh pr edit`), follow the `github-pr` skill.

## Format

```markdown
> <What the MR does, in one sentence.> <Anything the merger must do or wait for, if there is something.>

## Why

<The problem, in two or three sentences. What is broken or blocked today. Link the MR this unblocks or depends on.>

## What changed

- <One bullet per behavior change. Lead with the thing that changed.>
- <Security trade-offs and open risks go here as bullets, not in a separate section.>
```

No other headings. If the repo has an MR template, keep its headings instead
of Why and What changed, put the TLDR blockquote above the first one, and
still apply the steps and the cut list below.

## Steps

1. Read the full diff against the target branch and every commit in the MR,
   not only the top commit or the old description.
2. Draft from the diff. Treat the old description as a hint. Check every
   claim you keep against the code, and fix or drop the ones the diff doesn't
   support.
3. Cut hard (see below). Aim for about 10 to 15 lines of body.
4. Write the body to a temp file, update the PR with `--body-file`
   (`glab mr update --description-file` on GitLab),
   then delete the file.
5. Tell the user what you cut that might still matter to someone, such as a
   merge order or a post-merge check, so they can put it somewhere else.

## What goes where

**TLDR.** The outcome, plus any action that blocks or follows the merge: a
prerequisite MR, a manual job to run after merge, a required migration. No
background.

**Why.** The current problem and who it blocks. One link to the related MR
is enough. Don't explain the design here.

**What changed.** Group by behavior, not by file. Use a bold label such as
`**IAM:**` or `**CI:**` only when the bullets cover clearly different areas.
Keep the constraints a reviewer would ask about, like "it gets no
`eks:UpdateAccessEntry` because that action can't be restricted". Keep known
gaps and open risks. Docs changes get one bullet at most.

## Cut

- Test plans, plan output counts, and lint results. CI shows these. If a repo
  template has a test plan heading, keep it and list only the one to three
  checks a reviewer can't see in CI, such as a manual step after merge.
- Implementation notes the code or README already covers.
- Where a fact came from (API references, service JSON URLs).
- Full merge-order chains across several MRs. Name only the MR that must go
  first.
- Comparisons with other open or draft MRs.
- Notes about merge conflicts with other MRs.
- Quota math and other trivia that doesn't change the review.

## Example

```markdown
> Lets the CI roles give vended `app-*` roles EKS access limited to their namespace. After merge, run the manual `bootstrap-ci-roles` job on `master`.

## Why

app-environments [!17](…) gives each vended `app-*` role an EKS access entry for its environment's namespace. That code runs as `ci-deploy` (apply) and `ci-plan` (plan), and neither role can manage access entries today. Merge this before !17.

## What changed

- `ci-deploy` can create and delete access entries, but only for `app-*` roles, only as `STANDARD` with no Kubernetes groups or custom username, and only with the Edit or View policy scoped to a namespace. It gets no `eks:UpdateAccessEntry`, because that action can't be restricted.
- `ci-plan` can read the cluster and the `app-*` access entries, and gets cluster-wide View access so plans can refresh namespaces. View hides Secrets and RBAC, but anyone who can push a branch to a trusted project can read the cluster's Pods, ConfigMaps, and Ingresses.
- `terraform.tfvars.example` adds web-ui to `project_paths` to match the live roles. Remove it once app-environments [!18](…) merges.
- The README documents both roles' new EKS access.
```

This replaced a description about four times as long. It had a test plan,
plan counts, a four-step merge order across five repos, a comparison with a
draft MR, and a note about a README conflict.
