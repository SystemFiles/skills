"""Behavior tests for the sdd-qa `find-questions.py` helper."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script

SKILL = "sdd-qa"


def _seed_questions(workspace: Path, *, name: str = "01-questions-1-demo.md") -> Path:
    spec_dir = workspace / "docs" / "specs" / "01-spec-demo-feature"
    spec_dir.mkdir(parents=True)
    path = spec_dir / name
    path.write_text("# questions\n", encoding="utf-8")
    return path


def _run(workspace: Path, *args: str):
    return run_script(
        SKILL,
        "find-questions.py",
        *args,
        "--workspace",
        str(workspace),
    )


def test_finds_by_spec_number(tmp_path: Path) -> None:
    q = _seed_questions(tmp_path)
    proc = _run(tmp_path, "01")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["count"] == 1
    assert payload["paths"] == [str(q.resolve())]


def test_finds_by_feature_slug(tmp_path: Path) -> None:
    q = _seed_questions(tmp_path)
    proc = _run(tmp_path, "demo-feature")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["paths"] == [str(q.resolve())]


def test_finds_by_loose_questions_glob(tmp_path: Path) -> None:
    q = _seed_questions(tmp_path)
    proc = _run(tmp_path, "01*questions.md")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["paths"] == [str(q.resolve())]


def test_no_match_exits_one(tmp_path: Path) -> None:
    _seed_questions(tmp_path)
    proc = _run(tmp_path, "zz-missing")
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["count"] == 0
    assert payload["paths"] == []


def test_empty_query_lists_all(tmp_path: Path) -> None:
    q = _seed_questions(tmp_path)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["paths"] == [str(q.resolve())]
