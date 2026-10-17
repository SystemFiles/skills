---
name: jj-worktree
description: >-
  Create one isolated jj workspace per repository in scope and do the rest of
  the task there, so the main checkout stays untouched. Use whenever the user
  asks to work in a worktree, wants an isolated checkout, says not to touch
  the working copy, or invokes /jj-worktree. This replaces Cursor's git
  worktree lifecycle: use `jj workspace add` via the bundled script, never
  `git worktree`. One workspace per jj repo when several repos are in scope.
  Removing those workspaces is jj-worktree-cleanup, not this skill.
compatibility: Requires jj. Workspaces are stored under ~/.jj-worktrees (override with JJ_WORKTREE_HOME).
---

# jj-worktree

Cursor's `/worktree` isolates a task in a second checkout and leaves the
main one alone. These repos are jj. `git worktree add` does not create a jj
working-copy commit, so jj in that directory is the wrong repo state. The
lifecycle command is `jj workspace add`. Cleanup is a separate skill
(`jj-worktree-cleanup`) because creating a place to work and deleting it are
different requests.

The bundled script is the only way to create the workspace. It records the
path in a registry the cleanup skill trusts. A hand-run `jj workspace add`
is invisible to cleanup.

## Repos in scope

One workspace per jj repo the task will touch. Pass each as `--root`:

1. Paths the user named.
2. Otherwise every workspace folder this session has open.
3. Otherwise the jj repo that contains the current directory.

Do not walk the filesystem for extra repos. The script dedupes paths that
are the same repo and skips anything that is not a jj repo. If it skips a
path, say so. Do not create a git worktree for the skip. If every path is
skipped, stop. A pure git repo can use Cursor's own `/worktree`; this skill
does not run it.

If the current directory is already under `~/.jj-worktrees` (or
`JJ_WORKTREE_HOME`), do the task there. A second workspace needs the user to
ask for one (`--force-nested`).

## Create

Run this from the skill directory (the one that contains this file):

```bash
python3 "<skill-dir>/scripts/jj_worktree.py" create \
  --name "<slug>" \
  --root "<repo>" \
  [--root "<repo-2>" ...] \
  [--revision <rev>]
```

`--name` is a short slug for the task (`auth-fix`), shared by every repo in
this call. Omit it only when the user did not say what the work is.

Stdout is JSON.

- `status: ok` — workspaces were created. Do the task.
- `status: error` — do not start the task. Show `message`. If `workspaces`
  is non-empty, a later create only half-finished; tell the user the
  `session` id so cleanup can remove it.
- `skipped` — paths that were not jj repos.
- Each workspace has `repo`, `name`, `path`, `change_id`, `warnings`,
  `git_worktree`, and `setup`.

Show warnings before editing. Two of them change what the user should expect:

- The main checkout has changes. Default `jj workspace add` parents the new
  working-copy commit on the parents of `@`, so those edits stay in the main
  checkout. That is the same split as a git worktree. Pass `--revision @`
  only when the user wants the new workspace to start from the current
  snapshot. `--revision` is valid for a single `--root`.
- `git_worktree` is false. This jj did not attach a git checkout to the
  new workspace (0.45 has no `--colocate` on `jj workspace add`). Git tools
  will not see it. Do not paper over that with `git worktree add`.

The new directory is `~/.jj-worktrees/<repo-key>/<name>`, outside the repo.
Inside the repo, jj would snapshot the extra checkout into the main change.

If the repo has `.cursor/worktrees.json`, the script runs the same setup
Cursor would (`setup-worktree-unix` on macOS and Linux), with
`ROOT_WORKTREE_PATH` set to the main repo. A setup failure leaves the
workspace in place. Show it. Do not delete the workspace yourself.

## Do the work there

After `status: ok`, the main checkout is off limits for the rest of this
task.

- Read and write files only under each workspace `path`.
- Run `jj` with that directory as cwd, or `jj -R <path>`.
- A multi-repo task edits each repo only inside its own workspace.
- The new `@` is empty and described `jj-worktree: <name>`, so it is
  recognizable in `jj log` from every workspace of that repo. When the work
  is real, `jj describe` it in the workspace. Do not bookmark, push, or
  `jj abandon` unless the user asked.
- Do not `git add`, `git commit`, `git checkout`, or `git worktree`.
- Do not `jj workspace forget` here. That is the cleanup skill.
- Rewriting a commit that another workspace has checked out makes that
  workspace stale. `jj workspace update-stale` in the stale one. Do not
  rewrite the main workspace's `@` to do it.

Tell the user the session id, and each repo's workspace name and path,
before the first edit.

If the user invoked `/jj-worktree` with no task, create the workspace and
stop after that report.
