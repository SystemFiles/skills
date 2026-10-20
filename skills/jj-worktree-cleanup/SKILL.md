---
name: jj-worktree-cleanup
description: >-
  Remove jj workspaces created by the jj-worktree skill. Use whenever the
  user asks to clean up, delete, or remove those worktrees or workspaces, or
  invokes /jj-worktree-cleanup. Shows a plan and waits for the user to
  confirm, keeps any workspace with work no remote has unless the user says
  OK for it, then forgets the rest with `jj workspace forget` and deletes
  only directories that skill recorded. Does not use git worktree,
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
`workspaces[]` has `id`, `repo`, `name`, `path`, `change_id`, `exists`,
`tracked`, `empty`, `unpushed`, and `in_flight`. An empty list means there
is nothing to remove. Stop. Do not go hunt `jj workspace list` for other
checkouts.

`unpushed` lists the non-empty changes under the workspace's `@` that no
remote bookmark contains and the main checkout does not share (`change_id`,
`description`). It includes a dirty `@`. `in_flight: true` means that list
is not empty: deleting the workspace would leave work that exists only on
this machine. `in_flight: null` means the check failed (`unpushed_error`).
Treat that as in flight.

## Confirm (required checkpoint)

Never remove anything before the user answers this step. Asking for cleanup
is not the confirmation. Show the plan and stop:

- One row per workspace that would go: `name`, `repo`, `path`.
- For each in-flight workspace, its `unpushed` changes, and a plain
  statement that this work is not on any remote.

Then ask which workspaces to remove. Wait for the reply. No reply, or a
vague one, means remove nothing.

In-flight workspaces need an explicit "OK" from the user for that
workspace (for example "OK, remove auth-fix anyway"). A general "yes, clean
up" covers only the workspaces that are not in flight. Offer the safer
option first: push the work (`jj git push` from the workspace, with a
bookmark) and list again.

## Remove

Only after the user confirmed. Pass `--yes`:

```bash
python3 "<skill-dir>/scripts/cleanup.py" forget --yes --id "<id>" [--id "<id>" ...]
python3 "<skill-dir>/scripts/cleanup.py" forget --yes --session "<session>"
python3 "<skill-dir>/scripts/cleanup.py" forget --yes --all
```

Prefer `--id` with exactly the workspaces the user confirmed. `--all` only
when the user said to remove every recorded workspace.

Add `--allow-in-flight` only for ids the user gave that explicit OK. Run
those as a separate call so the flag cannot reach any other workspace:

```bash
python3 "<skill-dir>/scripts/cleanup.py" forget --yes --allow-in-flight --id "<id>"
```

Without `--yes`, `forget` deletes nothing and returns every selected
workspace as `action: pending` (a dry run).

Exit status:

- `0` / `status: ok` — every selected checkout was forgotten and its
  directory deleted.
- `2` / `status: needs_confirmation` — something was left in place.
  `action: pending` means `--yes` was missing. `action: kept` means the
  workspace is in flight and `--allow-in-flight` was missing. Show those
  rows with `unpushed` and go back to the checkpoint. Other rows in the same
  call may already be gone.
- `1` / `status: error` — nothing further should be deleted by hand. Show
  `message`. `action: refused` means the script thought the path was the
  repo itself or outside the worktree home.

`jj workspace forget` drops the working-copy pointer. It does not abandon
the change. The change ids are still in the local repo. Mention them.
Run `jj abandon <change_id>` only when the user wants the change itself
gone.

Do not `rm` a path the script did not just remove. Do not `jj workspace
forget default`. Do not forget a workspace that is not in the list output.
