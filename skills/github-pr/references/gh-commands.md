# gh PR command map

Verified against `gh` 2.100 and `jj` 0.45. Re-check with `gh <cmd> --help` when
something fails or a flag is missing.

Pass `-R/--repo "$REPO"` (from preflight) on every call. It accepts
`[HOST/]OWNER/REPO`. Also name the PR with a number, URL, or branch. Without
`-R`, gh asks git for remotes. Without a PR argument, gh asks git for the
current branch, and jj leaves git HEAD detached.

## Auth and repo

| Need | Command |
| --- | --- |
| Is this host logged in? | `gh auth status --hostname HOST` |
| Log in | User runs `gh auth login` (optional `--hostname`) |
| Default branch / fork parent | `gh repo view REPO --json defaultBranchRef,parent` |

## Create

```bash
gh pr create -R REPO --head HEAD --base BRANCH \
  --title TITLE --body-file FILE
```

| Flag | Use |
| --- | --- |
| `-t/--title` | Required for a written title |
| `-F/--body-file` | Body from a file; `-` reads stdin |
| `-B/--base` | Merge target |
| `-H/--head` | Always pass; `OWNER:BRANCH` for a fork → upstream PR |
| `-d/--draft` | Draft |
| `-l/--label` | Repeat or comma-separate |
| `-r/--reviewer` | Logins or `org/team` |
| `-a/--assignee` | Logins; `@me` to self-assign |
| `--no-maintainer-edit` | Block upstream maintainers from pushing to the head |
| `-T/--template` | Avoid; fill the template file yourself and pass `--body-file` |
| `--dry-run` | Prints the PR; may still push through git — avoid |
| `-f/--fill*` | **Do not use** (auto title/body) |
| `-w/--web` | **Do not use** |

## Update

```bash
gh pr edit -R REPO NUMBER|URL|BRANCH --title TITLE --body-file FILE
```

| Flag | Use |
| --- | --- |
| `--add-reviewer` / `--remove-reviewer` | Reviewers |
| `--add-label` / `--remove-label` | Labels |
| `--add-assignee` / `--remove-assignee` | Assignees |
| `-B/--base` | Retarget |

`gh pr ready -R REPO PR` marks ready; `--undo` converts back to draft.

## List / view / checks

```bash
gh pr list -R REPO --head BOOKMARK --json number,url,headRepositoryOwner
gh pr view -R REPO PR --json title,body,state,commits,reviews
gh pr checks -R REPO PR            # --watch to wait
```

`gh pr list --head` matches the branch name only, not `OWNER:BRANCH`; filter
on `headRepositoryOwner` for fork PRs.

## Comment / review

```bash
gh pr comment -R REPO PR --body-file FILE
gh pr review -R REPO PR --approve | --request-changes | --comment --body-file FILE
```

Line-level review comments need `gh api` against
`repos/OWNER/REPO/pulls/N/comments`.

## Merge / close

```bash
gh pr merge -R REPO PR --squash|--merge|--rebase
gh pr merge -R REPO PR --squash --auto
gh pr merge -R REPO PR --squash --match-head-commit "$(jj log -r BOOKMARK --no-graph -T commit_id)"
gh pr close -R REPO PR             # --comment, --delete-branch only if asked
```

## Issues

```bash
gh issue create -R REPO --title TITLE --body-file FILE   # -l, -a, --milestone
gh issue view -R REPO N --json title,body,labels
gh issue comment -R REPO N --body-file FILE
```

## jj side

| Need | Command |
| --- | --- |
| Commits in the PR | `jj log -r 'BASE..BOOKMARK'` (`BASE` like `main@origin`) |
| Diff vs base | `jj diff --from BASE --to BOOKMARK` (`--stat` for a summary) |
| Bookmark a commit | `jj bookmark create NAME -r REV` |
| Move bookmark forward | `jj bookmark move NAME --to REV` |
| Track an existing remote bookmark | `jj bookmark track NAME@REMOTE` |
| Push one bookmark | `jj git push -b BOOKMARK` (new bookmarks auto-track) |
| Add the fork parent | `jj git remote add upstream URL && jj git fetch --remote upstream` |
| Refresh remote state | `jj git fetch --all-remotes` |
