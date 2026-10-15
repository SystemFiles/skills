#!/usr/bin/env python3
"""List or forget jj-worktree workspaces.

The registry format lives in jj-worktree's jj_worktree.py. This wrapper only
forwards `list` and `forget` so a cleanup request cannot create a workspace.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def find_script() -> Path | None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "jj-worktree" / "scripts" / "jj_worktree.py",
        Path.home() / ".agents" / "skills" / "jj-worktree" / "scripts" / "jj_worktree.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"list", "forget"}:
        json.dump(
            {
                "status": "error",
                "message": "cleanup.py only runs list or forget.",
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 1
    script = find_script()
    if script is None:
        json.dump(
            {
                "status": "error",
                "message": "jj-worktree's jj_worktree.py is not installed next to this skill.",
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 1
    os.execv(sys.executable, [sys.executable, str(script), *argv])
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
