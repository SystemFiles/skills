---
name: github-pr
description: >-
  Create, update, view, comment on, or merge GitHub pull requests and issues
  with jj and the gh CLI, filling the repo's (or owner's) templates and using
  Conventional Commits. Use whenever the user mentions a pull request, PR,
  `gh pr`, opening or updating a PR, requesting review on GitHub, opening a PR
  from a fork to its upstream, or filing a GitHub issue.
compatibility: Requires jj (https://github.com/jj-vcs/jj) and an authenticated gh CLI (https://cli.github.com)
---

# GitHub pull requests and issues via jj + gh

Use `gh` for every GitHub operation and `jj` for every repo operation. Do not
invent curl/API calls and do not use `git`.

Pass `-R "$REPO"` (from preflight) to every `gh` command, and name the PR
explicitly with a number, URL, or branch. Without those, gh asks git for the
remote and the current branch, and jj leaves git HEAD detached, so gh's
"current branch" defaults fail.

Read [references/gh-commands.md](references/gh-commands.md) when you need exact
flags for a verb. Re-run `gh <cmd> --help` if a flag looks unfamiliar; CLI
versions drift.

Write every PR description, on create or update, with the
`useful-mr-descriptions` skill (section 4). Apply the `write-better` skill to
titles, descriptions, issues, and any comment the user will read.

## Why this shape

A PR is a review artifact, not a dump of the commit log. Title and body have
to cover **every commit since the base**, not just the top one. Templates
exist because the project already decided what reviewers need — inventing a
parallel format makes them hunt. `--fill` is faster and worse: it skips that
judgment.

## Hard rules

- Do not update git or jj config.
- Do not overwrite remote commits. `jj git push` acts like
  `git push --force-with-lease`, so when `push.state` is `behind` or
  `diverged`, confirm with the user before pushing.
- Do not describe, squash, rebase, or move commits or bookmarks unless the
  user asked. Only commits up to the bookmark are in the PR.
- Do not `jj git push --allow-empty-description` or `--allow-private`. Fix the
  commits instead.
- Do not run `gh auth login` with a token you were given in chat. If auth
  fails, tell the user to run `gh auth login` themselves.
- Do not `--fill`, `--fill-first`, or `--fill-verbose`. They overwrite a
  written body.
- Do not `--web`. It drops the flow into a browser.
- Do not approve, merge, or close unless the user explicitly asked.
- Do not create a second open PR for the same head.

## 1. Preflight

Run the bundled script from the **repo working tree**, not the skill directory:

```bash
python3 <path-to-this-skill>/scripts/pr-context.py [BOOKMARK] [--target-repo OWNER/REPO]
```

Pass `BOOKMARK` when the user named one, or to pick from
`bookmark_candidates`. Otherwise the script uses the bookmark nearest `@`
above the default branch.

Pass `--target-repo` to open the PR somewhere other than the push remote's
repo — usually the fork parent. Preflight warns when the push repo is a fork;
ask which repo the user wants before you create anything.

Honor `status`:

- `error` — show `message` and stop. Do not fall back to git.
- `warning` — show `message` and ask before continuing.
- `ok` — continue.

Fields you will use:

- `repo` — the PR's repo; pass as `-R "$REPO"` to every gh command.
- `head` — pass as `--head`. `OWNER:BOOKMARK` for a cross-repo PR.
- `bookmark` — the jj bookmark to push. `null` means none was found or several
  tied; `warnings` says which, and `suggested_bookmark_rev` is the commit to
  bookmark.
- `default_branch` — the target repo's default branch, the base unless the
  user names another.
- `base` — `<default_branch>@<remote>`, the base as a jj revset.
- `parent` — the push repo's fork parent, if any.
- `push` — whether `bookmark` is on the push remote: `state` is `not_pushed`,
  `synced`, `ahead`, `behind`, or `diverged`. `tracked` says whether jj tracks
  the remote bookmark.
- `commits` — every commit in `base..bookmark`.
- `changes_above_bookmark` — non-empty commits between the bookmark and `@`.
  They are not in the PR.
- `existing_prs` — open PRs from this head.
- `templates` — PR templates in the repo, else in the owner's `.github` repo
  (`source: owner-default`).

Use these; do not re-probe the same facts by hand.

When the user names a PR by number or URL (view, comment, review, merge,
close), a missing bookmark is not a blocker; still take `-R` from `repo`.

If `gh` is missing: `brew install gh`, then `gh auth login`. If `jj` is
missing: `brew install jj`. If the repo is a plain git clone, the user can run
`jj git init --colocate`.

## 2. jj context

Read the full change against the base:

```bash
jj log -r "$BASE..$BOOKMARK"
jj diff --from "$BASE" --to "$BOOKMARK" --stat
jj diff --from "$BASE" --to "$BOOKMARK"
```

Resolve preflight warnings with the user before pushing:

- No bookmark: propose a Conventional-Commits-style name (`feat/<topic>`,
  `fix/<topic>`), then `jj bookmark create <name> -r <suggested_bookmark_rev>`.
- `changes_above_bookmark`: ask whether they belong in the PR. If yes, run the
  `jj bookmark move` command from the warning.
- Commits without a description or with conflicts: `jj git push` refuses them.
  Help the user describe or resolve them.

Commit messages follow Conventional Commits:
`<type>(<optional scope>): <description>`.

Push before create/update so GitHub sees the commits:

```bash
jj git push -b "$BOOKMARK"
```

Push only the PR bookmark. A bare `jj git push` pushes every tracked bookmark
in range. New bookmarks start tracking on first push. If the push fails its
lease check, run `jj git fetch` and rerun preflight.

## 3. Route the request

### Create

If `existing_prs` is non-empty: show the URL(s). Do not open another. Offer to
update the existing PR instead.

Otherwise:

1. Draft title + body (section 4).
2. Write the body to a temp file. Do not commit it.
3. Create non-interactively:

```bash
gh pr create \
  -R "$REPO" \
  --head "$HEAD" \
  --base "$BASE_BRANCH" \
  --title "$TITLE" \
  --body-file "$BODY_FILE"
```

Always pass `--head`: gh's default is the current git branch, which does not
exist in a jj repo, and gh will offer to push through git when it cannot find
the head on the remote.

Add flags only when the user asked, or when a related issue/label/reviewer is
already in scope:

- `--draft` — draft
- `-l` / `--label` — labels
- `-r` / `--reviewer` — reviewers (logins or `org/team`)
- `-a` / `--assignee` — assignees (`@me` to self-assign)
- `--no-maintainer-edit` — only if asked, for cross-repo PRs

Link an issue by putting `Closes #N` in the body, not with a flag.

Return the PR URL. That is the deliverable.

### Update

```bash
gh pr edit -R "$REPO" <number|url|branch> --title "$TITLE" --body-file "$BODY_FILE"
```

Same description rules as create. `gh pr ready` / `gh pr ready --undo` toggles
draft. `--add-reviewer` / `--remove-reviewer`, `--add-label` /
`--remove-label`, `--add-assignee` / `--remove-assignee`, `-B` retargets.

### View / list

```bash
gh pr view -R "$REPO" <number|url|branch>     # add --json <fields> to parse
gh pr list -R "$REPO"                          # --head, --author @me, --draft, --state
gh pr checks -R "$REPO" <number|url|branch>
```

### Comment

```bash
gh pr comment -R "$REPO" <number|url|branch> --body-file "$BODY_FILE"
```

### Review

Only on an explicit ask:

```bash
gh pr review -R "$REPO" <number> --approve           # or --request-changes / --comment, with --body-file
```

### Merge

Only on an explicit ask. Pick the method the repo uses (`--squash`, `--merge`,
or `--rebase`). `--auto` waits for required checks. To merge only what the
user just reviewed, pass
`--match-head-commit "$(jj log -r "$BOOKMARK" --no-graph -T commit_id)"`.
`--delete-branch` and `--admin` only if asked. Afterward, `jj git fetch`.

### Close

Only on an explicit ask. Confirm the PR, then
`gh pr close -R "$REPO" <number|url|branch>`.

## 4. Title and description

Read **all** of `commits` and the full diff against the base (section 2), not
just the top commit.

Follow the `useful-mr-descriptions` skill before drafting any description,
with or without a template. Its steps, its rules for what to keep and cut, and
its TLDR blockquote apply in both cases. The template only decides the
headings.

**Template first.** If `templates` is non-empty, fill one:

- `source: repo` — read the file at `<root>/<path>`.
- `source: owner-default` — read it with
  `gh api repos/<repo>/contents/<path> --jq .content | base64 -d`.
- Several files: use the one the user named, else ask.

Keep the template headings. Put the TLDR blockquote above the first heading.
Fill every section from the actual changes. Keep HTML comments that hold
writing rules out of the final body, but follow them. Leave a section empty
only when the work truly has nothing for it — do not delete headings the
project uses as a checklist. Tick checklist items only for checks you ran.

**No template:** use the `useful-mr-descriptions` format as written: a TLDR
blockquote, then `## Why` and `## What changed`.

Title: Conventional Commits, `<type>(<optional scope>): <description>`. Short,
specific, one line. Many repos lint PR titles.

## 5. Issues

Use the repo's `.github/ISSUE_TEMPLATE/` if it has one, else the owner's
`.github` repo (`gh api repos/<owner>/.github/contents/.github/ISSUE_TEMPLATE`).
Without either, use:

- Summary
- Acceptance Criteria (if applicable)
- Additional sources / Notes (if applicable)

```bash
gh issue create -R "$REPO" --title "$TITLE" --body-file "$BODY_FILE"
```

## 6. Afterward

Give the user the PR or issue URL (or the action result). Do not open a
browser unless they asked.
