"""Behavior tests for the github-pr `pr-context.py` preflight script.

Runs the script against a throwaway colocated jj repo with a fake `gh` on
PATH, so no network or GitHub auth is needed.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import GIT_ENV, commit_file, git, init_repo, requires, run_script

SKILL = "github-pr"
SCRIPT = "pr-context.py"

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
fixtures = json.load(open(os.environ["FAKE_GH_FIXTURES"]))
if args[:2] == ["auth", "status"]:
    sys.exit(0)
if args[:2] == ["repo", "view"]:
    repo = args[2].split("/", 1)[1]
    if repo in fixtures["repos"]:
        print(json.dumps(fixtures["repos"][repo])); sys.exit(0)
    sys.exit(1)
if args[:2] == ["pr", "list"]:
    print(json.dumps(fixtures.get("prs", []))); sys.exit(0)
if args[0] == "api":
    path = args[-1]
    if path in fixtures.get("api", {}):
        print(json.dumps(fixtures["api"][path])); sys.exit(0)
    sys.exit(1)
sys.exit(2)
'''

FORK = {
    "nameWithOwner": "me/proj",
    "defaultBranchRef": {"name": "main"},
    "parent": {"owner": {"login": "up"}, "name": "proj"},
}
PARENT = {"nameWithOwner": "up/proj", "defaultBranchRef": {"name": "main"}, "parent": None}


def jj(repo: Path, env: dict[str, str], *args: str) -> str:
    return subprocess.run(
        ["jj", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def setup(tmp_path: Path):
    repo = init_repo(tmp_path / "proj")
    commit_file(repo, "README.md", "v1\n", "chore: initial")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "update-ref", "refs/remotes/upstream/main", "HEAD")
    git(repo, "remote", "add", "origin", "git@github.com:me/proj.git")
    git(repo, "remote", "add", "upstream", "https://github.com/up/proj.git")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH, encoding="utf-8")
    gh.chmod(0o755)

    jj_config = tmp_path / "jj.toml"
    jj_config.write_text(
        '[user]\nname = "Test User"\nemail = "test@example.com"\n', encoding="utf-8"
    )
    env = {
        **GIT_ENV,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "JJ_CONFIG": str(jj_config),
        "FAKE_GH_FIXTURES": str(tmp_path / "fixtures.json"),
    }
    jj(repo, env, "git", "init", "--colocate")
    jj(repo, env, "new", "main@origin", "-m", "feat: add thing")
    (repo / "thing.txt").write_text("x\n", encoding="utf-8")
    jj(repo, env, "bookmark", "create", "feat/thing", "-r", "@")

    def write_fixtures(**fixtures) -> None:
        Path(env["FAKE_GH_FIXTURES"]).write_text(json.dumps(fixtures), encoding="utf-8")

    return repo, env, write_fixtures


def preflight(repo: Path, env: dict[str, str], *args: str) -> tuple[int, dict]:
    proc = run_script(SKILL, SCRIPT, *args, cwd=repo, env=env)
    return proc.returncode, json.loads(proc.stdout)


@requires("jj")
def test_fork_to_parent_uses_owner_head_and_parent_base(setup) -> None:
    repo, env, write_fixtures = setup
    write_fixtures(
        repos={"me/proj": FORK, "up/proj": PARENT},
        prs=[
            {"number": 1, "url": "u1", "headRefName": "feat/thing", "headRepositoryOwner": {"login": "other"}},
            {"number": 2, "url": "u2", "headRefName": "feat/thing", "headRepositoryOwner": {"login": "me"}},
        ],
        api={
            "repos/up/.github/contents/.github": [
                {"type": "file", "name": "PULL_REQUEST_TEMPLATE.md", "path": ".github/PULL_REQUEST_TEMPLATE.md"}
            ]
        },
    )

    rc, out = preflight(repo, env, "--target-repo", "up/proj")

    assert rc == 0, out
    assert out["repo"] == "github.com/up/proj"
    assert out["head"] == "me:feat/thing"
    assert out["base"] == "main@upstream"
    assert [c["subject"] for c in out["commits"]] == ["feat: add thing"]
    assert [pr["number"] for pr in out["existing_prs"]] == [2]
    assert out["templates"] == [
        {"source": "owner-default", "repo": "up/.github", "path": ".github/PULL_REQUEST_TEMPLATE.md"}
    ]


@requires("jj")
def test_same_repo_on_fork_warns_about_parent_and_prefers_repo_template(setup) -> None:
    repo, env, write_fixtures = setup
    write_fixtures(repos={"me/proj": FORK})
    (repo / ".github").mkdir()
    (repo / ".github" / "pull_request_template.md").write_text("## Why\n", encoding="utf-8")

    rc, out = preflight(repo, env)

    assert rc == 0, out
    assert out["status"] == "warning"
    assert "--target-repo up/proj" in out["message"]
    assert out["head"] == "feat/thing"
    assert out["base"] == "main@origin"
    assert out["templates"] == [{"source": "repo", "path": ".github/pull_request_template.md"}]


@requires("jj")
def test_target_without_matching_remote_fails_with_hint(setup) -> None:
    repo, env, write_fixtures = setup
    write_fixtures(repos={"me/proj": FORK, "elsewhere/proj": {**PARENT, "nameWithOwner": "elsewhere/proj"}})

    rc, out = preflight(repo, env, "--target-repo", "elsewhere/proj")

    assert rc == 1
    assert out["status"] == "error"
    assert "jj git remote add upstream" in out["message"]
