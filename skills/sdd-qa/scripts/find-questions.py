#!/usr/bin/env python3
"""Find SDD questions markdown files under docs/specs/."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

QUESTIONS_RE = "*-questions*.md"


def specs_root(workspace: Path) -> Path:
    return workspace / "docs" / "specs"


def collect(workspace: Path) -> list[Path]:
    root = specs_root(workspace)
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob(QUESTIONS_RE) if p.is_file())


def matches(query: str, workspace: Path) -> list[Path]:
    all_files = collect(workspace)
    q = query.strip()
    if not q:
        return all_files

    as_path = Path(q)
    if as_path.is_file():
        return [as_path.resolve()]
    candidate = workspace / q
    if candidate.is_file():
        return [candidate.resolve()]

    patterns = [q]
    # `01*questions.md` should still hit `01-questions-1-feature.md`
    if "questions" in q and q.endswith(".md") and "questions*." not in q:
        patterns.append(q.replace("questions.md", "questions*.md"))

    found: set[Path] = set()
    for pattern in patterns:
        for base in (specs_root(workspace), workspace):
            for p in list(base.glob(pattern)) + list(base.rglob(pattern)):
                if p.is_file() and "questions" in p.name:
                    found.add(p.resolve())
        for p in all_files:
            rel = str(p.relative_to(workspace))
            if fnmatch.fnmatch(p.name, pattern) or fnmatch.fnmatch(rel, pattern):
                found.add(p.resolve())
            # Allow patterns anchored under docs/specs/
            if fnmatch.fnmatch(f"docs/specs/{p.name}", pattern) or fnmatch.fnmatch(
                f"docs/specs/{p.parent.name}/{p.name}", pattern
            ):
                found.add(p.resolve())

    if found:
        return sorted(found)

    needle = q.lower()
    return [
        p
        for p in all_files
        if needle in p.name.lower()
        or needle in str(p.relative_to(workspace)).lower()
        or needle in p.parent.name.lower()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help="Spec number, slug, path, or glob (e.g. 01, dataflow-slack, '01*questions.md')",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Repo root (default: cwd)",
    )
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    found = matches(args.query, workspace)
    print(
        json.dumps(
            {
                "workspace": str(workspace),
                "query": args.query,
                "count": len(found),
                "paths": [str(p) for p in found],
            },
            indent=2,
        )
    )
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())
