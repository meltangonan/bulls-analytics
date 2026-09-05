"""Exercise runner selection and worktree reporting in disposable repositories."""
from pathlib import Path
import shutil
import shlex
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def git(path, *args):
    return subprocess.run(
        ["git", "-C", str(path), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    primary = tmp_path / "sample repo"
    primary.mkdir()
    git(primary, "init", "-b", "main")
    git(primary, "config", "user.name", "Tool test")
    git(primary, "config", "user.email", "tools@example.invalid")
    (primary / "scripts").mkdir()
    (primary / "tests").mkdir()
    for source in ("run_tests.sh", "pytest.ini", "scripts/check_worktrees.sh"):
        shutil.copy2(ROOT / source, primary / source)
    (primary / ".gitignore").write_text("venv/\ncache/\noutput/\n__pycache__/\n.pytest_cache/\n")
    (primary / "tests/test_first.py").write_text(
        "def test_one():\n    assert True\n\ndef test_two():\n    assert True\n"
    )
    (primary / "tests/test_second.py").write_text("def test_three():\n    assert True\n")
    git(primary, "add", "run_tests.sh", "pytest.ini", "scripts", "tests", ".gitignore")
    git(primary, "commit", "-m", "fixture")
    (primary / "venv/bin").mkdir(parents=True)
    launcher = primary / "venv/bin/python"
    launcher.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' "$@"\n')
    launcher.chmod(0o755)
    return primary


@pytest.mark.parametrize("args, expected", [
    ([], ["test_first.py::test_one", "test_first.py::test_two", "test_second.py::test_three"]),
    (["-k", "test_three"], ["test_second.py::test_three"]),
    (["tests/test_first.py"], ["test_first.py::test_one", "test_first.py::test_two"]),
    (["tests/test_first.py::test_two"], ["test_first.py::test_two"]),
])
def test_runner_selects_only_requested_tests_in_linked_tree(repo, args, expected):
    linked = repo.parent / "outside shared folder"
    git(repo, "worktree", "add", "-b", "post", str(linked))
    result = subprocess.run(
        [str(linked / "run_tests.sh"), "--collect-only", "-q", *args],
        cwd=repo.parent, capture_output=True, text=True, check=True,
    )
    selected = [line.removeprefix("tests/") for line in result.stdout.splitlines() if "::test_" in line]
    assert selected == expected


def test_runner_does_not_fall_back_to_full_suite_for_invalid_target(repo):
    result = subprocess.run(
        [str(repo / "run_tests.sh"), "tests/missing.py"], capture_output=True, text=True
    )
    assert result.returncode == 4
    assert "file or directory not found" in result.stderr


def test_inventory_covers_linked_detached_orphan_and_missing_paths(repo):
    sibling_root = repo.parent / f"{repo.name}-worktrees"
    linked = sibling_root / "post"
    detached = repo.parent / "external detached"
    missing = sibling_root / "missing"
    orphan = sibling_root / "orphan"
    git(repo, "worktree", "add", "-b", "post", str(linked))
    git(repo, "worktree", "add", "--detach", str(detached))
    git(repo, "worktree", "add", "-b", "missing", str(missing))
    shutil.rmtree(missing)  # Fixture only: simulate an interrupted external cleanup.
    orphan.mkdir()
    (linked / "cache").mkdir()
    (linked / "cache/source.csv").write_text("expensive source\n")
    (linked / "output").mkdir()
    (linked / "output/chart.png").write_bytes(b"fixture")
    (orphan / "cache").mkdir()
    (orphan / "cache/raw.csv").write_text("orphaned source\n")
    primary_report = subprocess.check_output([str(repo / "scripts/check_worktrees.sh")], text=True)
    linked_report = subprocess.check_output([str(linked / "scripts/check_worktrees.sh")], text=True)
    assert linked_report == primary_report
    rows = {line.split("\t")[0]: line for line in primary_report.splitlines() if "\t" in line}
    assert set(rows) == {"WORKTREE", str(linked), str(detached), str(missing), str(orphan)}
    assert "\t0\t1\t1\tLIVE" in rows[str(linked)]
    assert "detached HEAD" in rows[str(detached)]
    assert "REVIEW" in rows[str(detached)]
    assert "PRUNABLE" in rows[str(missing)] or "MISSING" in rows[str(missing)]
    assert "\t?\t0\t1\tORPHAN" in rows[str(orphan)]
    assert "SAVED" not in primary_report


def test_inventory_treats_cache_alone_and_unmerged_commits_as_live(repo):
    cached = repo.parent / "cached"
    unmerged = repo.parent / "unmerged"
    git(repo, "worktree", "add", "-b", "cached", str(cached))
    git(repo, "worktree", "add", "-b", "unmerged", str(unmerged))
    (cached / "cache").mkdir()
    (cached / "cache/raw.csv").write_text("source\n")
    (unmerged / "new.txt").write_text("change\n")
    git(unmerged, "add", "new.txt")
    git(unmerged, "commit", "-m", "unmerged work")
    report = subprocess.check_output([str(repo / "scripts/check_worktrees.sh")], text=True)
    rows = {line.split("\t")[0]: line for line in report.splitlines() if "\t" in line}
    assert "\t0\t0\t1\tLIVE" in rows[str(cached)]
    assert "LIVE — HEAD not confirmed contained in main" in rows[str(unmerged)]
