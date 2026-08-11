#!/usr/bin/env python3
"""PR feedback Q&A session log under ``.scratch/pr-feedback-qa/``.

Commands:
  ensure-gitignore --repo-root PATH
  init --repo-root PATH --slug SLUG --source-type file|pr --source REF
       [--repo OWNER/REPO] [--pr-number N]
  resume --repo-root PATH --slug SLUG
  set-findings --repo-root PATH --slug SLUG --findings-file PATH
  record --repo-root PATH --slug SLUG --stdin-json
  clarify --repo-root PATH --slug SLUG --finding-id N --question Q --answer A
  summary --repo-root PATH --slug SLUG
  add-issue --repo-root PATH --slug SLUG --finding-id N|--parent
            --url URL --number N [--title T]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SESSION_VERSION = 1
SCRATCH_DIR = ".scratch"
SESSION_DIR = "pr-feedback-qa"
GITIGNORE_ENTRIES = (".scratch/",)
DISPOSITIONS = frozenset({"address", "skip", "github_issue"})


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def session_dir(repo_root: Path) -> Path:
    return repo_root / SCRATCH_DIR / SESSION_DIR


def session_path(repo_root: Path, slug: str) -> Path:
    safe = slug.strip().replace("/", "-")
    if not safe:
        raise ValueError("slug must be non-empty")
    return session_dir(repo_root) / f"{safe}.json"


def _ignored_scratch(text: str) -> bool:
    matched = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        if negated:
            line = line[1:]
        bare = line.lstrip("/").rstrip("/")
        if bare in {".scratch", "scratch"}:
            matched = not negated
    return matched


def ensure_gitignore(repo_root: Path) -> str:
    path = repo_root / ".gitignore"
    if not path.is_file():
        return "no-gitignore"
    text = path.read_text(encoding="utf-8")
    if _ignored_scratch(text):
        return "already-present"
    sep = "" if text.endswith("\n") or text == "" else "\n"
    block = "\n".join(GITIGNORE_ENTRIES) + "\n"
    path.write_text(f"{text}{sep}{block}", encoding="utf-8")
    return "appended"


def empty_session(
    *,
    slug: str,
    source_type: str,
    source_ref: str,
    repo: str | None = None,
    pr_number: int | None = None,
) -> dict[str, Any]:
    now = utc_now()
    return {
        "version": SESSION_VERSION,
        "slug": slug,
        "created_at": now,
        "updated_at": now,
        "source": {
            "type": source_type,
            "ref": source_ref,
            "repo": repo,
            "pr_number": pr_number,
        },
        "status": "in_progress",
        "current_index": 0,
        "findings": [],
        "decisions": [],
        "clarifications": [],
        "github_issues": [],
        "summary": None,
    }


def validate_session(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("session must be a JSON object")
    required = {
        "version",
        "slug",
        "created_at",
        "updated_at",
        "source",
        "status",
        "current_index",
        "findings",
        "decisions",
        "clarifications",
        "github_issues",
        "summary",
    }
    missing = required - data.keys()
    if missing:
        raise ValueError(f"missing keys: {sorted(missing)}")
    if data["version"] != SESSION_VERSION:
        raise ValueError(f"unsupported version: {data['version']}")
    source = data["source"]
    if not isinstance(source, dict) or source.get("type") not in {"file", "pr"}:
        raise ValueError("source.type must be file or pr")
    if not isinstance(source.get("ref"), str) or not source["ref"].strip():
        raise ValueError("source.ref must be a non-empty string")
    if not isinstance(data["findings"], list):
        raise ValueError("findings must be a list")
    if not isinstance(data["decisions"], list):
        raise ValueError("decisions must be a list")
    return data


def load_session(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON: {exc}") from exc
    return validate_session(raw)


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = utc_now()
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
        prefix=f".{path.stem}.",
        suffix=".tmp",
    ) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def decided_ids(session: dict[str, Any]) -> set[int]:
    return {d["finding_id"] for d in session["decisions"] if "finding_id" in d}


def advance_current_index(session: dict[str, Any]) -> None:
    done = decided_ids(session)
    findings = session["findings"]
    for i, finding in enumerate(findings):
        if finding["id"] not in done:
            session["current_index"] = i
            session["status"] = "in_progress"
            return
    session["current_index"] = len(findings)
    if findings and len(done) >= len(findings):
        session["status"] = "summary_ready"


def render_summary_markdown(session: dict[str, Any]) -> str:
    by_id = {d["finding_id"]: d for d in session["decisions"]}
    lines = [
        "**Decisions**",
        "",
        "| # | Disposition | Notes |",
        "| --- | --- | --- |",
    ]
    label_map = {
        "address": "Address",
        "skip": "Skip",
        "github_issue": "GitHub Issue",
    }
    for finding in session["findings"]:
        fid = finding["id"]
        decision = by_id.get(fid)
        if not decision:
            lines.append(f"| {fid} | — | undecided |")
            continue
        disp = label_map.get(decision["disposition"], decision["disposition"])
        notes_parts: list[str] = []
        if decision.get("fix_choice"):
            notes_parts.append(str(decision["fix_choice"]))
        if decision.get("notes"):
            notes_parts.append(str(decision["notes"]))
        labels = decision.get("labels") or []
        if labels:
            notes_parts.append(", ".join(labels))
        notes = "; ".join(notes_parts) if notes_parts else "—"
        lines.append(f"| {fid} | {disp} | {notes} |")
    queued = sum(1 for d in session["decisions"] if d["disposition"] == "github_issue")
    lines.extend(["", f"**Queued GitHub issues:** {queued}"])
    return "\n".join(lines) + "\n"


def cmd_ensure_gitignore(args: argparse.Namespace) -> int:
    print(ensure_gitignore(args.repo_root.resolve()))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    root = args.repo_root.resolve()
    path = session_path(root, args.slug)
    if path.exists() and not args.force:
        print(f"error: session exists: {path} (use --force)", file=sys.stderr)
        return 1
    ensure_gitignore(root)
    session = empty_session(
        slug=args.slug.strip(),
        source_type=args.source_type,
        source_ref=args.source,
        repo=args.repo,
        pr_number=args.pr_number,
    )
    atomic_write(path, session)
    print(path)
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    path = session_path(args.repo_root.resolve(), args.slug)
    if not path.is_file():
        print(f"error: session not found: {path}", file=sys.stderr)
        return 1
    try:
        session = load_session(path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(session, indent=2, ensure_ascii=False))
    return 0


def cmd_set_findings(args: argparse.Namespace) -> int:
    root = args.repo_root.resolve()
    path = session_path(root, args.slug)
    try:
        session = load_session(path)
        findings = json.loads(args.findings_file.read_text(encoding="utf-8"))
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not isinstance(findings, list):
        print("error: findings file must be a JSON array", file=sys.stderr)
        return 1
    for i, item in enumerate(findings, start=1):
        if not isinstance(item, dict):
            print(f"error: finding {i} must be an object", file=sys.stderr)
            return 1
        item.setdefault("id", i)
        for key in ("title", "summary", "sources"):
            if key not in item:
                print(f"error: finding {i} missing {key}", file=sys.stderr)
                return 1
    session["findings"] = findings
    session["decisions"] = []
    session["clarifications"] = []
    session["github_issues"] = []
    session["summary"] = None
    advance_current_index(session)
    atomic_write(path, session)
    print(path)
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    root = args.repo_root.resolve()
    path = session_path(root, args.slug)
    try:
        session = load_session(path)
        payload = json.load(sys.stdin)
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print("error: stdin must be a JSON object", file=sys.stderr)
        return 1
    try:
        finding_id = int(payload["finding_id"])
        disposition = payload["disposition"]
    except (KeyError, TypeError, ValueError):
        print("error: finding_id and disposition required", file=sys.stderr)
        return 1
    if disposition not in DISPOSITIONS:
        print(f"error: disposition must be one of {sorted(DISPOSITIONS)}", file=sys.stderr)
        return 1
    ids = {f["id"] for f in session["findings"]}
    if finding_id not in ids:
        print(f"error: unknown finding_id {finding_id}", file=sys.stderr)
        return 1
    session["decisions"] = [d for d in session["decisions"] if d["finding_id"] != finding_id]
    decision = {
        "finding_id": finding_id,
        "disposition": disposition,
        "fix_choice": payload.get("fix_choice"),
        "notes": payload.get("notes"),
        "labels": payload.get("labels") or [],
        "decided_at": utc_now(),
    }
    session["decisions"].append(decision)
    session["decisions"].sort(key=lambda d: d["finding_id"])
    advance_current_index(session)
    atomic_write(path, session)
    print(json.dumps(decision, indent=2, ensure_ascii=False))
    return 0


def cmd_clarify(args: argparse.Namespace) -> int:
    root = args.repo_root.resolve()
    path = session_path(root, args.slug)
    try:
        session = load_session(path)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    ids = {f["id"] for f in session["findings"]}
    if args.finding_id not in ids:
        print(f"error: unknown finding_id {args.finding_id}", file=sys.stderr)
        return 1
    entry = {
        "finding_id": args.finding_id,
        "question": args.question,
        "answer": args.answer,
        "at": utc_now(),
    }
    session["clarifications"].append(entry)
    atomic_write(path, session)
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    root = args.repo_root.resolve()
    path = session_path(root, args.slug)
    try:
        session = load_session(path)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    md = render_summary_markdown(session)
    session["summary"] = {"markdown": md, "generated_at": utc_now()}
    if session["status"] == "in_progress" and len(decided_ids(session)) >= len(
        session["findings"]
    ):
        session["status"] = "summary_ready"
    atomic_write(path, session)
    sys.stdout.write(md)
    return 0


def cmd_add_issue(args: argparse.Namespace) -> int:
    root = args.repo_root.resolve()
    path = session_path(root, args.slug)
    try:
        session = load_session(path)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finding_id = None if args.parent else args.finding_id
    if finding_id is None and not args.parent:
        print("error: pass --finding-id or --parent", file=sys.stderr)
        return 1
    if finding_id is not None:
        ids = {f["id"] for f in session["findings"]}
        if finding_id not in ids:
            print(f"error: unknown finding_id {finding_id}", file=sys.stderr)
            return 1
    entry = {
        "finding_id": finding_id,
        "url": args.url,
        "number": args.number,
        "title": args.title,
        "created_at": utc_now(),
    }
    session["github_issues"].append(entry)
    queued = {
        d["finding_id"]
        for d in session["decisions"]
        if d["disposition"] == "github_issue"
    }
    created = {
        i["finding_id"] for i in session["github_issues"] if i["finding_id"] is not None
    }
    if queued and queued <= created:
        session["status"] = "issues_created"
    atomic_write(path, session)
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    eg = sub.add_parser("ensure-gitignore", help="Append .scratch/ to .gitignore if needed")
    eg.add_argument("--repo-root", type=Path, default=Path.cwd())
    eg.set_defaults(func=cmd_ensure_gitignore)

    init = sub.add_parser("init", help="Create a new session JSON file")
    init.add_argument("--repo-root", type=Path, default=Path.cwd())
    init.add_argument("--slug", required=True)
    init.add_argument("--source-type", choices=("file", "pr"), required=True)
    init.add_argument("--source", required=True)
    init.add_argument("--repo", default=None)
    init.add_argument("--pr-number", type=int, default=None)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    resume = sub.add_parser("resume", help="Print an existing session")
    resume.add_argument("--repo-root", type=Path, default=Path.cwd())
    resume.add_argument("--slug", required=True)
    resume.set_defaults(func=cmd_resume)

    sf = sub.add_parser("set-findings", help="Replace findings list from a JSON file")
    sf.add_argument("--repo-root", type=Path, default=Path.cwd())
    sf.add_argument("--slug", required=True)
    sf.add_argument("--findings-file", type=Path, required=True)
    sf.set_defaults(func=cmd_set_findings)

    rec = sub.add_parser("record", help="Record a disposition from stdin JSON")
    rec.add_argument("--repo-root", type=Path, default=Path.cwd())
    rec.add_argument("--slug", required=True)
    rec.set_defaults(func=cmd_record)

    cl = sub.add_parser("clarify", help="Append a clarification Q&A pair")
    cl.add_argument("--repo-root", type=Path, default=Path.cwd())
    cl.add_argument("--slug", required=True)
    cl.add_argument("--finding-id", type=int, required=True)
    cl.add_argument("--question", required=True)
    cl.add_argument("--answer", required=True)
    cl.set_defaults(func=cmd_clarify)

    sm = sub.add_parser("summary", help="Write and print the decision summary table")
    sm.add_argument("--repo-root", type=Path, default=Path.cwd())
    sm.add_argument("--slug", required=True)
    sm.set_defaults(func=cmd_summary)

    ai = sub.add_parser("add-issue", help="Record a created GitHub issue URL")
    ai.add_argument("--repo-root", type=Path, default=Path.cwd())
    ai.add_argument("--slug", required=True)
    ai.add_argument("--finding-id", type=int, default=None)
    ai.add_argument("--parent", action="store_true")
    ai.add_argument("--url", required=True)
    ai.add_argument("--number", type=int, required=True)
    ai.add_argument("--title", default=None)
    ai.set_defaults(func=cmd_add_issue)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
