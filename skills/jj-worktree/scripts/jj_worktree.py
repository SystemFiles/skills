#!/usr/bin/env python3
"""Create, list, and forget jj workspaces for the jj-worktree skills.

Stdout is one JSON object. The registry is $JJ_WORKTREE_HOME/registry.json
(default ~/.jj-worktrees/registry.json). jj-worktree-cleanup forgets only
entries in that file, so create and remove have to go through this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_VERSION = 1


class Failure(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def emit(payload: dict, code: int) -> int:
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return code


def home_dir() -> Path:
    raw = os.environ.get("JJ_WORKTREE_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".jj-worktrees"


def registry_path() -> Path:
    return home_dir() / "registry.json"


def is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def is_strict_descendant(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r != parent_r and is_under(child_r, parent_r)


def jj(cwd: Path, *args: str, ignore_working_copy: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = ["jj", "--color=never", "--no-pager", "--config", "ui.log-word-wrap=false"]
    if ignore_working_copy:
        cmd.append("--ignore-working-copy")
    cmd.extend(args)
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def supports_colocate() -> bool:
    proc = subprocess.run(
        ["jj", "--color=never", "workspace", "add", "--help"],
        capture_output=True,
        text=True,
    )
    return "--colocate" in proc.stdout


def slugify(name: str) -> str:
    out = []
    dash = False
    for ch in name.strip().lower():
        if ch.isascii() and ch.isalnum():
            out.append(ch)
            dash = False
        elif not dash and out:
            out.append("-")
            dash = True
    return "".join(out).strip("-")[:40]


def default_name() -> str:
    return "wt-" + datetime.now().strftime("%Y%m%d-%H%M%S")


def read_registry_file(path: Path) -> dict:
    if not path.exists():
        return {"version": REGISTRY_VERSION, "workspaces": []}
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {"version": REGISTRY_VERSION, "workspaces": []}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Failure(f"Registry is corrupt ({path}): {exc}") from exc
    if data.get("version") != REGISTRY_VERSION:
        raise Failure(f"Unsupported registry version at {path}")
    if not isinstance(data.get("workspaces"), list):
        raise Failure(f"Registry at {path} has no workspaces list")
    return data


def update_registry(mutator) -> dict:
    home = home_dir()
    home.mkdir(parents=True, exist_ok=True)
    lock_path = home / "registry.lock"
    path = registry_path()
    try:
        import fcntl
    except ImportError:
        fcntl = None  # type: ignore[assignment]

    with lock_path.open("a", encoding="utf-8") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data = read_registry_file(path)
        mutator(data)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return data


def workspace_names(repo: Path) -> set[str]:
    proc = jj(repo, "workspace", "list", "-T", 'json(self) ++ "\n"', ignore_working_copy=True)
    if proc.returncode != 0:
        raise Failure(proc.stderr.strip() or "jj workspace list failed")
    names = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            names.add(json.loads(line)["name"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise Failure(f"Could not parse workspace list: {line}") from exc
    return names


def workspace_state(cwd: Path) -> tuple[bool | None, str | None, str | None]:
    """Return (empty, change_id, error). Snapshots the working copy on purpose."""
    proc = jj(cwd, "log", "-r", "@", "--no-graph", "-T", 'empty ++ "\n" ++ change_id.short()')
    if proc.returncode != 0:
        return None, None, proc.stderr.strip() or "jj log failed"
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if len(lines) < 2 or lines[0] not in {"true", "false"}:
        return None, None, f"unexpected jj log output: {proc.stdout!r}"
    return lines[0] == "true", lines[1], None


def unique_name(repo: Path, base: str) -> str:
    taken = workspace_names(repo)
    if base not in taken:
        return base
    for n in range(2, 50):
        candidate = f"{base}-{n}"
        if candidate not in taken:
            return candidate
    raise Failure(f"No free workspace name near {base}")


def repo_key(repo: Path) -> str:
    base = slugify(repo.name) or "repo"
    digest = hashlib.sha256(str(repo.resolve()).encode()).hexdigest()[:8]
    return f"{base}-{digest}"


def discover(roots: list[str]) -> tuple[list[Path], list[dict]]:
    repos: list[Path] = []
    skipped: list[dict] = []
    seen: set[Path] = set()
    for raw in roots:
        path = Path(raw).expanduser()
        if path.is_file():
            path = path.parent
        if not path.exists():
            skipped.append({"path": raw, "reason": "path does not exist"})
            continue
        proc = jj(path, "workspace", "root", ignore_working_copy=True)
        if proc.returncode != 0:
            skipped.append({"path": str(path), "reason": "not a jj repo"})
            continue
        root = Path(proc.stdout.strip()).resolve()
        if root in seen:
            continue
        seen.add(root)
        repos.append(root)
    return repos, skipped


def setup_spec(repo: Path) -> list[str]:
    path = repo / ".cursor" / "worktrees.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Failure(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise Failure(f"{path} must be a JSON object")
    keys = (
        ("setup-worktree-windows", "setup-worktree")
        if os.name == "nt"
        else ("setup-worktree-unix", "setup-worktree")
    )
    value = None
    for key in keys:
        if data.get(key):
            value = data[key]
            break
    if value is None:
        return []
    if isinstance(value, str):
        script = (path.parent / value).resolve()
        if not script.is_file():
            raise Failure(f"Setup script not found: {script}")
        return [shlex.quote(str(script))]
    if isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value):
        return list(value)
    raise Failure("setup-worktree must be a command array or a script path")


def run_setup(repo: Path, dest: Path, commands: list[str]) -> tuple[dict, list[str]]:
    if not commands:
        return {"ran": False}, []
    env = os.environ.copy()
    env["ROOT_WORKTREE_PATH"] = str(repo.resolve())
    results = []
    warnings = []
    for cmd in commands:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(dest),
            env=env,
            capture_output=True,
            text=True,
        )
        results.append(
            {
                "command": cmd,
                "exit_code": proc.returncode,
                "stderr": proc.stderr[-400:],
            }
        )
        if proc.returncode != 0:
            warnings.append(f"Setup command failed ({proc.returncode}): {cmd}")
            break
    return {"ran": True, "results": results}, warnings


def safe_rmtree(path: Path) -> None:
    home = home_dir()
    if not is_strict_descendant(path, home):
        raise Failure(f"Refusing to delete {path}: it is not under {home}")
    shutil.rmtree(path)


def add_one(
    repo: Path,
    base_name: str,
    session: str,
    revision: str | None,
    force_nested: bool,
) -> dict:
    home = home_dir()
    if is_strict_descendant(repo, home) and not force_nested:
        raise Failure(
            f"{repo} is already a jj-worktree workspace. "
            "Do the task there. Pass --force-nested only when the user asked for a second workspace."
        )
    name = unique_name(repo, base_name)
    if name == "default":
        raise Failure("Refusing workspace name 'default'.")
    dest = home / repo_key(repo) / name
    if dest.exists():
        raise Failure(f"Destination already exists: {dest}")
    if is_under(dest, repo) or is_under(repo, dest):
        raise Failure("Workspace path would nest inside the repo. Move JJ_WORKTREE_HOME outside it.")
    # Reject a bad setup file before jj creates the workspace.
    commands = setup_spec(repo)
    dest.parent.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    if revision is None:
        empty, _, err = workspace_state(repo)
        if err:
            warnings.append(f"Could not inspect the main checkout: {err}")
        elif empty is False:
            warnings.append(
                "Main checkout has changes. They stay there. "
                "This workspace starts from the parent of @. "
                "Pass --revision @ to start from the current snapshot instead."
            )

    cmd = ["workspace", "add", "--name", name, "-m", f"jj-worktree: {name}"]
    if revision:
        cmd.extend(["-r", revision])
    colocated = (repo / ".git").exists()
    if colocated and supports_colocate():
        cmd.append("--colocate")
    cmd.append(str(dest))
    proc = jj(repo, *cmd)
    if proc.returncode != 0:
        if name not in workspace_names(repo) and dest.exists():
            shutil.rmtree(dest)
            parent = dest.parent
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        detail = proc.stderr.strip() or proc.stdout.strip() or "jj workspace add failed"
        raise Failure(detail)

    git_worktree = (dest / ".git").exists()
    if colocated and not git_worktree:
        warnings.append(
            "This jj does not create a Git worktree for the new workspace. "
            "Git-based tools will not see it. Do not fix that with git worktree add."
        )

    empty, change_id, err = workspace_state(dest)
    if err:
        warnings.append(f"Workspace was created but jj log failed: {err}")

    setup, setup_warnings = run_setup(repo, dest, commands)
    warnings.extend(setup_warnings)

    record = {
        "id": str(uuid.uuid4()),
        "session": session,
        "name": name,
        "repo": str(repo.resolve()),
        "path": str(dest.resolve()),
        "revision": revision,
        "change_id": change_id,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    def add_record(data: dict) -> None:
        data["workspaces"].append(record)

    update_registry(add_record)
    return {
        **record,
        "empty": empty,
        "git_worktree": git_worktree,
        "setup": setup,
        "warnings": warnings,
    }


def cmd_create(args: argparse.Namespace) -> int:
    repos, skipped = discover(args.root)
    if args.revision and len(repos) > 1:
        return emit(
            {
                "status": "error",
                "message": "--revision applies to one repo. Pass a single --root.",
                "skipped": skipped,
            },
            1,
        )
    if not repos:
        return emit(
            {
                "status": "error",
                "message": "No jj repos in scope. Not creating a git worktree.",
                "skipped": skipped,
            },
            1,
        )
    base = slugify(args.name) if args.name else default_name()
    if not base or base == "default":
        return emit(
            {"status": "error", "message": "Pass a workspace name other than 'default'."},
            1,
        )
    session = str(uuid.uuid4())
    created = []
    failed = []
    for repo in repos:
        try:
            created.append(add_one(repo, base, session, args.revision, args.force_nested))
        except Failure as exc:
            failed.append({"repo": str(repo), "message": exc.message})
    payload = {
        "status": "error" if failed else "ok",
        "session": session,
        "name": base,
        "workspaces": created,
        "skipped": skipped,
        "failed": failed,
    }
    if failed:
        payload["message"] = (
            "Not every repo got a workspace. Do not start the task. "
            "Use jj-worktree-cleanup on this session to remove the ones that were created."
        )
        return emit(payload, 1)
    return emit(payload, 0)


def enrich(entry: dict) -> dict:
    path = Path(entry["path"])
    repo = Path(entry["repo"])
    info = {
        **entry,
        "exists": path.is_dir(),
        "tracked": False,
        "empty": None,
    }
    if repo.is_dir():
        try:
            info["tracked"] = entry["name"] in workspace_names(repo)
        except Failure as exc:
            info["track_error"] = exc.message
    if path.is_dir():
        empty, change_id, err = workspace_state(path)
        info["empty"] = empty
        if change_id:
            info["change_id"] = change_id
        if err:
            info["state_error"] = err
    return info


def cmd_list(args: argparse.Namespace) -> int:
    try:
        data = read_registry_file(registry_path())
    except Failure as exc:
        return emit({"status": "error", "message": exc.message}, 1)
    rows = data["workspaces"]
    if args.session:
        rows = [row for row in rows if row.get("session") == args.session]
    return emit({"status": "ok", "workspaces": [enrich(row) for row in rows]}, 0)


def forget_one(entry: dict, discard: bool) -> dict:
    for key in ("id", "session", "name", "repo", "path"):
        if not entry.get(key):
            return {"action": "error", "message": f"registry entry missing {key}", "entry": entry}
    repo = Path(entry["repo"])
    path = Path(entry["path"])
    name = entry["name"]
    result = {
        "id": entry["id"],
        "session": entry["session"],
        "name": name,
        "repo": str(repo),
        "path": str(path),
        "change_id": entry.get("change_id"),
    }
    try:
        if path.exists() and path.resolve() == repo.resolve():
            result["action"] = "refused"
            result["message"] = "path is the repo itself"
            return result
        if path.exists() and not is_strict_descendant(path, home_dir()):
            result["action"] = "refused"
            result["message"] = "path is outside the worktree home"
            return result
    except OSError as exc:
        result["action"] = "error"
        result["message"] = str(exc)
        return result

    if repo.is_dir():
        proc = jj(repo, "workspace", "root", "--name", name, ignore_working_copy=True)
        root_proc = jj(repo, "workspace", "root", ignore_working_copy=True)
        if (
            proc.returncode == 0
            and root_proc.returncode == 0
            and Path(proc.stdout.strip()).resolve() == Path(root_proc.stdout.strip()).resolve()
        ):
            result["action"] = "refused"
            result["message"] = "that name is the repo's own workspace"
            return result

    if path.is_dir():
        empty, change_id, err = workspace_state(path)
        if change_id:
            result["change_id"] = change_id
        if err or empty is None:
            result["action"] = "error"
            result["message"] = err or "could not tell whether the checkout has changes"
            return result
        result["empty"] = empty
        if not empty and not discard:
            result["action"] = "kept"
            result["message"] = "checkout has changes; left it in place"
            return result

    tracked = False
    if repo.is_dir():
        try:
            tracked = name in workspace_names(repo)
        except Failure as exc:
            result["action"] = "error"
            result["message"] = exc.message
            return result
    if tracked:
        proc = jj(repo, "workspace", "forget", name)
        if proc.returncode != 0:
            result["action"] = "error"
            result["message"] = proc.stderr.strip() or "jj workspace forget failed"
            return result

    if path.exists():
        try:
            safe_rmtree(path)
        except (Failure, OSError) as exc:
            result["action"] = "error"
            result["message"] = str(exc)
            return result

    result["action"] = "removed"
    return result


def cmd_forget(args: argparse.Namespace) -> int:
    try:
        data = read_registry_file(registry_path())
    except Failure as exc:
        return emit({"status": "error", "message": exc.message}, 1)
    rows = data["workspaces"]
    if args.all:
        chosen = list(rows)
        missing: list[str] = []
    elif args.session:
        chosen = [row for row in rows if row.get("session") == args.session]
        missing = []
    else:
        wanted = set(args.id)
        chosen = [row for row in rows if row.get("id") in wanted]
        missing = sorted(wanted - {row.get("id") for row in chosen})

    if args.all and not chosen:
        return emit(
            {
                "status": "ok",
                "results": [],
                "message": "No jj-worktree workspaces recorded.",
            },
            0,
        )
    if not chosen:
        return emit(
            {
                "status": "error",
                "message": "No matching workspaces.",
                "missing": missing,
            },
            1,
        )

    results = [forget_one(row, args.discard_checkout) for row in chosen]
    removed_ids = {row["id"] for row in results if row.get("action") == "removed"}
    if removed_ids:
        def drop(data: dict) -> None:
            data["workspaces"] = [
                row for row in data["workspaces"] if row.get("id") not in removed_ids
            ]

        try:
            update_registry(drop)
        except Failure as exc:
            return emit({"status": "error", "message": exc.message, "results": results}, 1)

    actions = {row.get("action") for row in results}
    if "error" in actions or "refused" in actions or missing:
        status, code = "error", 1
    elif "kept" in actions:
        status, code = "needs_confirmation", 2
    else:
        status, code = "ok", 0
    return emit({"status": status, "results": results, "missing": missing}, code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jj_worktree.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create", help="add one workspace per jj repo")
    create.add_argument("--root", action="append", required=True)
    create.add_argument("--name")
    create.add_argument("--revision")
    create.add_argument("--force-nested", action="store_true")

    listing = sub.add_parser("list", help="list workspaces this script created")
    listing.add_argument("--session")

    forget = sub.add_parser("forget", help="forget workspaces and delete their directories")
    group = forget.add_mutually_exclusive_group(required=True)
    group.add_argument("--session")
    group.add_argument("--id", action="append")
    group.add_argument("--all", action="store_true")
    forget.add_argument("--discard-checkout", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if shutil.which("jj") is None:
        return emit({"status": "error", "message": "jj is not on PATH."}, 1)
    try:
        if args.cmd == "create":
            return cmd_create(args)
        if args.cmd == "list":
            return cmd_list(args)
        if args.cmd == "forget":
            return cmd_forget(args)
    except Failure as exc:
        return emit({"status": "error", "message": exc.message}, 1)
    return emit({"status": "error", "message": f"unknown command {args.cmd}"}, 1)


if __name__ == "__main__":
    sys.exit(main())
