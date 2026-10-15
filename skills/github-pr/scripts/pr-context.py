#!/usr/bin/env python3
"""Gather jj + gh context for the github-pr skill.

Usage: pr-context.py [BOOKMARK] [--target-repo OWNER/REPO]

Reads the repo only through jj. In a jj-colocated repo git HEAD is always
detached, so git has no "current branch"; the PR head is the bookmark nearest
@ above the target's default branch (or BOOKMARK when given). gh gets an
explicit -R so it never infers the repo from git remotes.

--target-repo opens the PR against another repo (usually the fork parent).
The head then becomes OWNER:BOOKMARK and the base revset comes from the jj
remote whose URL points at the target repo.

JSON to stdout. Exit 0 on ok/warning, 1 on error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from typing import NoReturn

COMMIT_FIELDS = {
    "change_id": "json(change_id.short(12))",
    "commit_id": "json(commit_id.short(12))",
    "subject": "json(description.first_line())",
    "described": 'if(description, "true", "false")',
    "empty": "json(empty)",
    "conflict": "json(conflict)",
}
COMMIT_TEMPLATE = '"[" ++ ' + ' ++ "," ++ '.join(COMMIT_FIELDS.values()) + ' ++ "]"'

PR_FIELDS = "number,title,url,state,isDraft,headRefName,baseRefName,headRepositoryOwner"

# GitHub reads a PR template from the repo root, .github/, or docs/, and falls
# back to the owner's `.github` repo only when the repo has none.
TEMPLATE_DIRS = ("", ".github", "docs")
TEMPLATE_FILE = "pull_request_template.md"
TEMPLATE_MULTI_DIR = "pull_request_template"

# The first jj call snapshots the working copy; later calls reuse that snapshot.
_jj_snapshotted = False


def fail(message: str) -> NoReturn:
    print(json.dumps({"status": "error", "message": message}, indent=2))
    sys.exit(1)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True)


def jj(*args: str) -> str:
    global _jj_snapshotted
    flags = ["--no-pager", "--color", "never", "--config", "ui.log-word-wrap=false"]
    if _jj_snapshotted:
        flags.append("--ignore-working-copy")
    proc = run("jj", *flags, *args)
    if proc.returncode != 0:
        fail(f"jj {' '.join(args)} failed: {proc.stderr.strip()}")
    _jj_snapshotted = True
    return proc.stdout


def gh_json(*args: str) -> object | None:
    proc = run("gh", *args)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def lit(value: str) -> str:
    """Quote a value as a jj string literal."""
    return json.dumps(value, ensure_ascii=False)


def log(revset: str, template: str) -> list[str]:
    out = jj("log", "--no-graph", "-r", revset, "-T", f'{template} ++ "\\n"')
    return [line for line in out.splitlines() if line]


def change_ids(revset: str) -> list[str]:
    return log(revset, "change_id.short(12)")


def count(revset: str) -> int:
    return len(change_ids(revset))


def dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def bookmark_rev(name: str) -> str:
    return f"bookmarks(exact:{lit(name)})"


def remote_bookmark_rev(name: str, remote: str) -> str:
    return f"remote_bookmarks(exact:{lit(name)}, remote=exact:{lit(remote)})"


def parse_remote_url(url: str) -> tuple[str, str] | None:
    """Return (host, OWNER/REPO) from an ssh://, http(s)://, or scp-style URL."""
    if "://" in url:
        parts = urllib.parse.urlsplit(url)
        host, path = parts.hostname or "", parts.path
    else:
        match = re.match(r"^(?:[^@/]+@)?([^:/]+):(.+)$", url)
        if not match:
            return None
        host, path = match.groups()
    path = path.strip("/").removesuffix(".git")
    if not host or path.count("/") != 1:
        return None
    return host, path


def remotes() -> dict[str, str]:
    found: dict[str, str] = {}
    for line in jj("git", "remote", "list").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            found[parts[0]] = parts[1]
    if not found:
        fail("No git remote configured. Add one: jj git remote add origin <url>")
    return found


def push_remote(all_remotes: dict[str, str]) -> str:
    """Pick the remote `jj git push` would use."""
    configured = run("jj", "--no-pager", "--ignore-working-copy", "config", "get", "git.push")
    name = configured.stdout.strip() if configured.returncode == 0 else ""
    if not name:
        name = next(iter(all_remotes)) if len(all_remotes) == 1 else "origin"
    if name not in all_remotes:
        fail(f"Push remote {name!r} not found. Remotes: {', '.join(all_remotes)}. Set git.push or add it.")
    return name


def remote_for_repo(all_remotes: dict[str, str], host: str, repo: str) -> str | None:
    for name, url in all_remotes.items():
        parsed = parse_remote_url(url)
        if parsed and parsed[0].lower() == host.lower() and parsed[1].lower() == repo.lower():
            return name
    return None


def repo_info(host: str, repo: str) -> dict:
    """Ask GitHub: jj's trunk() is a local guess and can point elsewhere."""
    data = gh_json("repo", "view", f"{host}/{repo}", "--json", "nameWithOwner,defaultBranchRef,parent")
    if not isinstance(data, dict):
        fail(f"gh repo view {host}/{repo} failed. Check the remote URL and gh auth.")
    branch = (data.get("defaultBranchRef") or {}).get("name")
    if not branch:
        fail(f"GitHub returned no default branch for {repo}.")
    parent = data.get("parent") or None
    parent_name = None
    if parent:
        parent_name = f"{parent['owner']['login']}/{parent['name']}"
    return {"repo": data.get("nameWithOwner", repo), "default_branch": branch, "parent": parent_name}


def commits(revset: str) -> list[dict]:
    return [dict(zip(COMMIT_FIELDS, json.loads(line))) for line in log(revset, COMMIT_TEMPLATE)]


def push_state(bookmark: str, remote: str) -> dict:
    local = bookmark_rev(bookmark)
    remote_rev = remote_bookmark_rev(bookmark, remote)
    if count(remote_rev) == 0:
        return {"remote": remote, "state": "not_pushed", "tracked": False, "ahead": None, "behind": None}

    ahead = count(f"{remote_rev}..{local}")
    behind = count(f"{local}..{remote_rev}")
    if ahead and behind:
        state = "diverged"
    elif ahead:
        state = "ahead"
    elif behind:
        state = "behind"
    else:
        state = "synced"

    tracked_out = jj(
        "bookmark", "list", "--all-remotes", f"exact:{lit(bookmark)}",
        "-T", f'if(remote, if(remote == {lit(remote)}, tracked ++ "\\n"))',
    ).split()
    tracked = bool(tracked_out) and tracked_out[0] == "true"
    return {"remote": remote, "state": state, "tracked": tracked, "ahead": ahead, "behind": behind}


def existing_prs(host: str, target: str, bookmark: str, head_owner: str) -> list[dict]:
    prs = gh_json(
        "pr", "list", "-R", f"{host}/{target}", "--head", bookmark,
        "--state", "open", "--json", PR_FIELDS,
    )
    if not isinstance(prs, list):
        return []
    # `--head` filters by branch name only, so drop same-named branches from other forks.
    return [
        {k: pr.get(k) for k in ("number", "title", "url", "isDraft", "headRefName", "baseRefName")}
        for pr in prs
        if ((pr.get("headRepositoryOwner") or {}).get("login") or "").lower() == head_owner.lower()
    ]


def is_template(name: str) -> bool:
    return name.lower() == TEMPLATE_FILE


def local_templates(root: str) -> list[dict]:
    found: list[dict] = []
    for sub in TEMPLATE_DIRS:
        directory = os.path.join(root, sub) if sub else root
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            rel = os.path.join(sub, name) if sub else name
            if os.path.isfile(path) and is_template(name):
                found.append({"source": "repo", "path": rel})
            elif os.path.isdir(path) and name.lower() == TEMPLATE_MULTI_DIR:
                found.extend(
                    {"source": "repo", "path": os.path.join(rel, child)}
                    for child in sorted(os.listdir(path))
                    if child.endswith(".md") and os.path.isfile(os.path.join(path, child))
                )
    return found


def owner_templates(host: str, owner: str) -> list[dict]:
    """PR templates from OWNER/.github, which GitHub uses when the repo has none."""
    found: list[dict] = []
    for sub in TEMPLATE_DIRS:
        listing = gh_json("api", "--hostname", host, f"repos/{owner}/.github/contents/{sub}")
        if not isinstance(listing, list):
            continue
        for entry in listing:
            if entry.get("type") == "file" and is_template(entry.get("name", "")):
                found.append({"source": "owner-default", "repo": f"{owner}/.github", "path": entry["path"]})
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bookmark", nargs="?")
    parser.add_argument("--target-repo", help="OWNER/REPO to open the PR against (default: the push remote's repo)")
    args = parser.parse_args()

    for tool, hint in (("jj", "brew install jj"), ("gh", "brew install gh, then gh auth login")):
        if not shutil.which(tool):
            fail(f"{tool} is not installed. Install it ({hint}).")

    root_proc = run("jj", "--no-pager", "root")
    if root_proc.returncode != 0:
        fail("Not inside a jj repo. For a git clone, run: jj git init --colocate")
    root = root_proc.stdout.strip()
    jj("log", "--no-graph", "-r", "@", "-T", '""')

    all_remotes = remotes()
    remote = push_remote(all_remotes)
    parsed = parse_remote_url(all_remotes[remote])
    if not parsed:
        fail(f"Remote {remote} URL {all_remotes[remote]!r} is not a GitHub OWNER/REPO URL.")
    host, push_repo = parsed

    if run("gh", "auth", "status", "--hostname", host).returncode != 0:
        fail(f"gh is not authenticated for {host}. Run: gh auth login --hostname {host}")

    push_info = repo_info(host, push_repo)
    push_repo = push_info["repo"]
    head_owner = push_repo.split("/")[0]

    target = args.target_repo or push_repo
    cross_repo = target.lower() != push_repo.lower()
    if cross_repo:
        target_info = repo_info(host, target)
        target = target_info["repo"]
        base_remote = remote_for_repo(all_remotes, host, target)
        if not base_remote:
            fail(
                f"No jj remote points at {target}. Add and fetch it: "
                f"jj git remote add upstream git@{host}:{target}.git && jj git fetch --remote upstream"
            )
    else:
        target_info = push_info
        base_remote = remote

    default = target_info["default_branch"]
    base = remote_bookmark_rev(default, base_remote)
    if count(base) == 0:
        fail(f"{default}@{base_remote} is not in the local repo. Run: jj git fetch --remote {base_remote}")

    warnings: list[str] = []
    if not cross_repo and push_info["parent"]:
        warnings.append(
            f"{push_repo} is a fork of {push_info['parent']}. This PR targets the fork. "
            f"To target the parent, re-run with --target-repo {push_info['parent']}."
        )

    bookmark: str | None = None
    candidates: list[str] = []
    suggested_rev: str | None = None

    if args.bookmark:
        if count(bookmark_rev(args.bookmark)) == 0:
            fail(f"No local bookmark {args.bookmark!r}. If it exists on {remote}, run: jj bookmark track {args.bookmark}@{remote}")
        bookmark = args.bookmark
    else:
        candidates = dedupe(log(
            f"heads(bookmarks() & ({base}..@))",
            'local_bookmarks.map(|b| b.name()).join("\\n")',
        ))
        if len(candidates) == 1:
            bookmark = candidates[0]
            candidates = []
        elif candidates:
            warnings.append(
                f"Several bookmarks sit at the top of the stack: {', '.join(candidates)}. "
                "Re-run with the one to use as the first argument."
            )
        else:
            heads = change_ids(f"heads(({base}..@) ~ empty())")
            if heads:
                suggested_rev = heads[0]
                warnings.append(
                    f"No bookmark between {default}@{base_remote} and @. "
                    f"Create one before opening a PR: jj bookmark create <name> -r {suggested_rev}"
                )
            else:
                warnings.append(f"@ has no changes on top of {default}@{base_remote}; nothing to open a PR for.")

    stack: list[dict] = []
    above: list[str] = []
    push: dict | None = None
    prs: list[dict] = []

    if bookmark:
        local = bookmark_rev(bookmark)
        if count(local) > 1:
            fail(f"Bookmark {bookmark!r} is conflicted. Inspect with: jj bookmark list {bookmark}")

        if bookmark == default and not cross_repo:
            warnings.append(f"Bookmark {bookmark} is the default branch. PRs should come from a feature bookmark.")

        stack = commits(f"{base}..{local}")
        if not any(not c["empty"] for c in stack):
            warnings.append(f"{bookmark} has no changes relative to {default}@{base_remote}.")
        undescribed = [c["change_id"] for c in stack if not c["described"]]
        if undescribed:
            warnings.append(
                f"Commits without a description: {', '.join(undescribed)}. "
                "jj git push refuses them; add one with jj describe <change_id>."
            )
        conflicted = [c["change_id"] for c in stack if c["conflict"]]
        if conflicted:
            warnings.append(f"Commits with conflicts: {', '.join(conflicted)}. jj git push refuses them.")

        if count(f"{local} & ::@"):
            above = change_ids(f"({local}..@) ~ empty()")
            if above:
                top = change_ids(f"heads(({local}..@) ~ empty())")[0]
                warnings.append(
                    f"{len(above)} change(s) between {bookmark} and @ are not in the PR. "
                    f"To include them: jj bookmark move {bookmark} --to {top}"
                )

        push = push_state(bookmark, remote)
        if push["state"] != "not_pushed" and not push["tracked"]:
            warnings.append(f"{bookmark}@{remote} exists but is not tracked. Run: jj bookmark track {bookmark}@{remote}")
        if push["state"] in ("behind", "diverged"):
            warnings.append(
                f"{bookmark}@{remote} has {push['behind']} commit(s) local {bookmark} lacks "
                "(someone else pushed, or pushed commits were rewritten). "
                "jj git push would replace them; confirm before pushing."
            )

        prs = existing_prs(host, target, bookmark, head_owner)

    templates = local_templates(root) or owner_templates(host, target.split("/")[0])

    print(json.dumps({
        "status": "warning" if warnings else "ok",
        "message": "\n".join(warnings) or "Ready.",
        "warnings": warnings,
        "root": root,
        "host": host,
        "repo": f"{host}/{target}",
        "push_repo": f"{host}/{push_repo}",
        "parent": push_info["parent"],
        "remote": {"name": remote, "url": all_remotes[remote]},
        "default_branch": default,
        "base": f"{default}@{base_remote}",
        "bookmark": bookmark,
        "head": (f"{head_owner}:{bookmark}" if cross_repo else bookmark) if bookmark else None,
        "bookmark_candidates": candidates,
        "suggested_bookmark_rev": suggested_rev,
        "push": push,
        "commits": stack,
        "changes_above_bookmark": above,
        "existing_prs": prs,
        "templates": templates,
    }, indent=2))


if __name__ == "__main__":
    main()
