---
name: jj-worktree-cleanup
description: >-
  Remove jj workspaces created by the jj-worktree skill. Use whenever the
  user asks to clean up, delete, or remove those worktrees or workspaces, or
  invokes /jj-worktree-cleanup. Forgets them with `jj workspace forget` and
  deletes only directories that skill recorded. Does not use git worktree,
  and does not remove the main checkout or unrelated jj workspaces. Not for
  general code cleanup, branch deletion, or wiping a repo.
compatibility: Requires jj and the jj-worktree skill installed beside this one. Registry is ~/.jj-worktrees (override with JJ_WORKTREE_HOME).
---

# jj-worktree-cleanup

`jj-worktree` records every workspace it creates. This skill removes only
those. Other jj workspaces, including the repo's own checkout, are not ours
to delete. `git worktree remove` does not forget a jj workspace.

The wrapper only forwards `list` and `forget` to `jj-worktree`'s script, so
this command cannot create a workspace. Both skills need to be installed
next to each other (or jj-worktree under `~/.agents/skills/jj-worktree`).

## List

```bash
python3 "<skill-dir>/scripts/cleanup.py" list
python3 "<skill-dir>/scripts/cleanup.py" list --session "<session>"
```

`<skill-dir>` is the directory that contains this file. Stdout is JSON.
`workspaces[]` has `repo`, `name`, `path`, `change_id`, `exists`, `tracked`,
and `empty`. An empty list means there is nothing to remove. Stop. Do not
go hunt `jj workspace list` for other checkouts.

## Remove

The user already asked for cleanup. Empty checkouts (`empty: true`) can go
without a second question. A checkout with changes stays until they confirm,
because the directory is the working copy of a real change.

```bash
python3 "<skill-dir>/scripts/cleanup.py" forget --session "<session>"
python3 "<skill-dir>/scripts/cleanup.py" forget --id "<id>" [--id "<id>" ...]
python3 "<skill-dir>/scripts/cleanup.py" forget --all
```

`--all` only when the user said to remove every recorded workspace, not
when they named one task.

Exit status:

- `0` / `status: ok` — every selected checkout was forgotten and its
  directory deleted.
- `2` / `status: needs_confirmation` — one or more checkouts have changes.
  `results[]` with `action: kept` include `change_id`, `name`, and `path`.
  Show those and ask. Empty ones in the same call are already gone.
- `1` / `status: error` — nothing further should be deleted by hand. Show
  `message`. `action: refused` means the script thought the path was the
  repo itself or outside the worktree home.

After the user agrees to drop a dirty checkout:

```bash
python3 "<skill-dir>/scripts/cleanup.py" forget --id "<id>" --discard-checkout
```

`jj workspace forget` drops the working-copy pointer. It does not abandon
the change. The change id in the result is still in the repo. Mention it.
Run `jj abandon <change_id>` only when the user wants the change itself
gone.

Do not `rm` a path the script did not just remove. Do not `jj workspace
forget default`. Do not forget a workspace that is not in the list output.
