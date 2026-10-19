"""Behavior tests for jj-worktree create/list/forget.

The scripts talk to a real jj. Each test gets its own JJ_CONFIG and
JJ_WORKTREE_HOME so nothing lands in the developer's home directory.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from conftest import GIT_ENV, commit_file, git, init_repo, requires, run_script


def jj_env(tmp: Path) -> dict[str, str]:
    config = tmp / "jj.toml"
    config.write_text(
        '[user]\nname = "Test User"\nemail = "test@example.com"\n',
        encoding="utf-8",
    )
    home = tmp / "wt-home"
    home.mkdir()
    return {**GIT_ENV, "JJ_CONFIG": str(config), "JJ_WORKTREE_HOME": str(home)}


def jj(repo: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["jj", "--color=never", "--no-pager", *args],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def make_jj_repo(path: Path, env: dict[str, str]) -> Path:
    init_repo(path)
    commit_file(path, "README.md", "v1\n", "chore: initial")
    subprocess.run(
        ["jj", "--color=never", "--no-pager", "git", "init", "--colocate"],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    # jj 0.45 leaves the imported files on @ with parent root. An empty @ on
    # top of that commit is what a normal editing session looks like.
    empty = jj(path, env, "log", "-r", "@", "--no-graph", "-T", "empty").stdout.strip()
    if empty != "true":
        jj(path, env, "new")
    return path


def run_json(
    skill: str, script: str, *args: str, env: dict[str, str], cwd: Path | None = None
) -> tuple[int, dict]:
    proc = run_script(skill, script, *args, env=env, cwd=cwd)
    assert proc.stdout, proc.stderr
    return proc.returncode, json.loads(proc.stdout)


@requires("jj")
def test_create_leaves_main_checkout_dirty_and_workspace_clean(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = make_jj_repo(tmp_path / "repo", env)
    readme = repo / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "dirty\n", encoding="utf-8")

    code, payload = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "iso", "--root", str(repo), env=env
    )

    assert code == 0, payload
    ws = payload["workspaces"][0]
    assert ws["name"] == "iso"
    assert (Path(ws["path"]) / "README.md").read_text(encoding="utf-8") == "v1\n"
    assert readme.read_text(encoding="utf-8") == "v1\ndirty\n"
    assert any("They stay there." in warning for warning in ws["warnings"])
    assert Path(ws["path"]).is_relative_to(Path(env["JJ_WORKTREE_HOME"]))
    assert not Path(ws["path"]).is_relative_to(repo)
    names = jj(repo, env, "workspace", "list", "-T", 'name ++ "\n"').stdout
    assert "iso" in names
    if "--colocate" not in subprocess.run(
        ["jj", "workspace", "add", "--help"], capture_output=True, text=True
    ).stdout:
        assert ws["git_worktree"] is False
        assert any("git worktree add" in warning for warning in ws["warnings"])


@requires("jj")
def test_revision_at_starts_from_current_snapshot(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = make_jj_repo(tmp_path / "repo", env)
    (repo / "README.md").write_text("v1\ndirty\n", encoding="utf-8")

    code, payload = run_json(
        "jj-worktree",
        "jj_worktree.py",
        "create",
        "--name", "from-here",
        "--revision", "@",
        "--root", str(repo),
        env=env,
    )

    assert code == 0, payload
    ws = payload["workspaces"][0]
    assert "dirty" in (Path(ws["path"]) / "README.md").read_text(encoding="utf-8")
    assert not any("They stay there." in warning for warning in ws["warnings"])


@requires("jj")
def test_one_session_per_repo_in_scope(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    first = make_jj_repo(tmp_path / "one", env)
    second = make_jj_repo(tmp_path / "two", env)

    code, payload = run_json(
        "jj-worktree",
        "jj_worktree.py",
        "create",
        "--name", "both",
        "--root", str(first),
        "--root", str(second),
        "--root", str(first / "README.md"),
        env=env,
    )

    assert code == 0, payload
    assert len(payload["workspaces"]) == 2
    assert payload["workspaces"][0]["session"] == payload["workspaces"][1]["session"]
    assert {row["repo"] for row in payload["workspaces"]} == {
        str(first.resolve()),
        str(second.resolve()),
    }
    assert payload["skipped"] == []

    code, listed = run_json(
        "jj-worktree-cleanup",
        "cleanup.py",
        "list",
        "--session",
        payload["session"],
        env=env,
    )
    assert code == 0
    assert len(listed["workspaces"]) == 2
    assert {row["in_flight"] for row in listed["workspaces"]} == {False}

    code, dry = run_json(
        "jj-worktree-cleanup",
        "cleanup.py",
        "forget",
        "--session",
        payload["session"],
        env=env,
    )
    assert code == 2, dry
    assert dry["status"] == "needs_confirmation"
    assert {row["action"] for row in dry["results"]} == {"pending"}
    assert Path(payload["workspaces"][0]["path"]).is_dir()
    assert Path(payload["workspaces"][1]["path"]).is_dir()

    code, forgotten = run_json(
        "jj-worktree-cleanup",
        "cleanup.py",
        "forget",
        "--yes",
        "--session",
        payload["session"],
        env=env,
    )
    assert code == 0, forgotten
    assert {row["action"] for row in forgotten["results"]} == {"removed"}
    assert not Path(payload["workspaces"][0]["path"]).exists()
    assert not Path(payload["workspaces"][1]["path"]).exists()
    code, left = run_json("jj-worktree", "jj_worktree.py", "list", env=env)
    assert code == 0
    assert left["workspaces"] == []


@requires("jj")
def test_git_repo_does_not_grow_a_worktree(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = init_repo(tmp_path / "gitonly")
    commit_file(repo, "README.md", "v1\n", "chore: initial")
    before = git(repo, "worktree", "list").stdout

    code, payload = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "nope", "--root", str(repo), env=env
    )

    assert code == 1
    assert not payload.get("workspaces")
    assert "not a jj repo" in payload["skipped"][0]["reason"]
    assert git(repo, "worktree", "list").stdout == before


@requires("jj")
def test_dirty_checkout_is_in_flight_until_explicit_ok(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = make_jj_repo(tmp_path / "repo", env)
    code, payload = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "keep", "--root", str(repo), env=env
    )
    assert code == 0, payload
    ws = payload["workspaces"][0]
    (Path(ws["path"]) / "extra.txt").write_text("x\n", encoding="utf-8")

    code, listed = run_json("jj-worktree", "jj_worktree.py", "list", env=env)
    assert code == 0
    assert listed["workspaces"][0]["in_flight"] is True
    assert listed["workspaces"][0]["unpushed"][0]["description"] == "jj-worktree: keep"

    code, kept = run_json(
        "jj-worktree", "jj_worktree.py", "forget", "--yes", "--id", ws["id"], env=env
    )
    assert code == 2
    assert kept["results"][0]["action"] == "kept"
    assert Path(ws["path"]).is_dir()

    code, dropped = run_json(
        "jj-worktree",
        "jj_worktree.py",
        "forget",
        "--yes",
        "--allow-in-flight",
        "--id", ws["id"],
        env=env,
    )
    assert code == 0, dropped
    assert dropped["results"][0]["action"] == "removed"
    assert not Path(ws["path"]).exists()
    change_id = dropped["results"][0]["change_id"]
    still = jj(repo, env, "log", "-r", change_id, "--no-graph", "-T", "change_id.short()")
    assert change_id in still.stdout
    assert (repo / "README.md").is_file()


@requires("jj")
def test_committed_but_unpushed_work_is_in_flight(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = make_jj_repo(tmp_path / "repo", env)
    code, payload = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "wip", "--root", str(repo), env=env
    )
    assert code == 0, payload
    ws = payload["workspaces"][0]
    wt = Path(ws["path"])
    (wt / "extra.txt").write_text("x\n", encoding="utf-8")
    jj(wt, env, "commit", "-m", "feat: local only")

    code, kept = run_json(
        "jj-worktree", "jj_worktree.py", "forget", "--yes", "--id", ws["id"], env=env
    )
    assert code == 2, kept
    row = kept["results"][0]
    assert row["empty"] is True
    assert row["action"] == "kept"
    assert [c["description"] for c in row["unpushed"]] == ["feat: local only"]
    assert wt.is_dir()


@requires("jj")
def test_pushed_work_is_not_in_flight(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = make_jj_repo(tmp_path / "repo", env)
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", "-q", str(remote))
    jj(repo, env, "git", "remote", "add", "origin", str(remote))
    code, payload = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "pushed", "--root", str(repo), env=env
    )
    assert code == 0, payload
    ws = payload["workspaces"][0]
    wt = Path(ws["path"])
    (wt / "extra.txt").write_text("x\n", encoding="utf-8")
    jj(wt, env, "commit", "-m", "feat: pushed")
    jj(wt, env, "bookmark", "create", "feat-pushed", "-r", "@-")
    jj(wt, env, "git", "push", "-b", "feat-pushed")

    code, removed = run_json(
        "jj-worktree", "jj_worktree.py", "forget", "--yes", "--id", ws["id"], env=env
    )
    assert code == 0, removed
    assert removed["results"][0]["action"] == "removed"
    assert removed["results"][0]["in_flight"] is False
    assert not wt.exists()


@requires("jj")
def test_forget_refuses_to_delete_the_repo_itself(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = make_jj_repo(tmp_path / "repo", env)
    code, payload = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "safe", "--root", str(repo), env=env
    )
    assert code == 0, payload
    registry = Path(env["JJ_WORKTREE_HOME"]) / "registry.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["workspaces"][0]["path"] = str(repo)
    registry.write_text(json.dumps(data), encoding="utf-8")

    code, result = run_json(
        "jj-worktree",
        "jj_worktree.py",
        "forget",
        "--id",
        payload["workspaces"][0]["id"],
        env=env,
    )

    assert code == 1
    assert result["results"][0]["action"] == "refused"
    assert (repo / "README.md").is_file()
    assert (repo / ".jj").exists()


@requires("jj")
def test_setup_runs_in_the_new_workspace(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = make_jj_repo(tmp_path / "repo", env)
    cursor = repo / ".cursor"
    cursor.mkdir()
    (cursor / "worktrees.json").write_text(
        json.dumps(
            {
                "setup-worktree-unix": [
                    "python3 -c 'import os; open(\"setup-marker.txt\",\"w\").write(os.environ[\"ROOT_WORKTREE_PATH\"])'"
                ]
            }
        ),
        encoding="utf-8",
    )

    code, payload = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "setup", "--root", str(repo), env=env
    )

    assert code == 0, payload
    marker = Path(payload["workspaces"][0]["path"]) / "setup-marker.txt"
    assert marker.read_text(encoding="utf-8") == str(repo.resolve())
    assert payload["workspaces"][0]["setup"]["ran"] is True


@requires("jj")
def test_bad_setup_file_does_not_create_a_workspace(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = make_jj_repo(tmp_path / "repo", env)
    cursor = repo / ".cursor"
    cursor.mkdir()
    (cursor / "worktrees.json").write_text("{", encoding="utf-8")

    code, payload = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "bad", "--root", str(repo), env=env
    )

    assert code == 1
    assert payload["failed"][0]["message"]
    names = jj(repo, env, "workspace", "list", "-T", 'name ++ "\n"').stdout.split()
    assert names == ["default"]


@requires("jj")
def test_name_collision_and_nested_workspace_are_rejected(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    repo = make_jj_repo(tmp_path / "repo", env)
    code, first = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "demo", "--root", str(repo), env=env
    )
    assert code == 0, first
    code, second = run_json(
        "jj-worktree", "jj_worktree.py", "create", "--name", "demo", "--root", str(repo), env=env
    )
    assert code == 0, second
    assert second["workspaces"][0]["name"] == "demo-2"

    code, nested = run_json(
        "jj-worktree",
        "jj_worktree.py",
        "create",
        "--name", "again",
        "--root", first["workspaces"][0]["path"],
        env=env,
    )
    assert code == 1
    assert "already a jj-worktree workspace" in nested["failed"][0]["message"]


@requires("jj")
def test_revision_is_rejected_for_multiple_repos(tmp_path: Path) -> None:
    env = jj_env(tmp_path)
    first = make_jj_repo(tmp_path / "one", env)
    second = make_jj_repo(tmp_path / "two", env)

    code, payload = run_json(
        "jj-worktree",
        "jj_worktree.py",
        "create",
        "--name", "nope",
        "--revision", "@",
        "--root", str(first),
        "--root", str(second),
        env=env,
    )

    assert code == 1
    assert "single --root" in payload["message"]
    assert "workspaces" not in payload or payload.get("workspaces") in (None, [])


def test_cleanup_rejects_create() -> None:
    code, payload = run_json(
        "jj-worktree-cleanup", "cleanup.py", "create", "--name", "x", env={}
    )
    assert code == 1
    assert "list or forget" in payload["message"]
