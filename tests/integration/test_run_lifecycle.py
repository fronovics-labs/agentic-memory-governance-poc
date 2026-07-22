"""Disposable-repository coverage for frozen baselines and run worktrees."""

import json
import subprocess
from pathlib import Path

import pytest

from lab.cli import main
from lab.runs.baseline import default_runs_root, freeze_baseline, verify_baseline
from lab.runs.manifest import RunManifest, read_json
from lab.runs.workspace import archive_run, create_run, reset_run, verify_run


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(root), *arguments),
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "platform"
    files = {
        ".python-version": "3.12\n",
        "AGENTS.md": "instructions\n",
        "ARCHITECTURE.md": "architecture\n",
        "CLAUDE.md": "claude\n",
        "pyproject.toml": "[project]\nname='test-platform'\nversion='1'\n",
        "uv.lock": "version = 1\n",
        "scripts/lab": "#!/bin/sh\n",
        "src/lab/cli.py": "# cli\n",
        "agents/IMPLEMENTER.md": "implement\n",
        ".org-memory/items/policy.md": "memory\n",
        ".claude/settings.json": "{}\n",
        ".codex/hooks.json": "{}\n",
        "src/lab/governance/checks/platform.py": "# checks\n",
        "sample_app/service.py": "VALUE = 1\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "lab@example.test")
    _git(root, "config", "user.name", "Lab Test")
    _git(root, "add", "-f", ".")
    _git(root, "commit", "-m", "baseline")
    return root, default_runs_root(root)


def test_freeze_records_every_required_identity_and_verify_detects_changes(
    tmp_path: Path,
) -> None:
    root, runs_root = _repository(tmp_path)
    manifest_path = freeze_baseline(root, runs_root, "platform-v1")
    value = read_json(manifest_path)

    assert value["git_commit"] == _git(root, "rev-parse", "HEAD")
    assert value["git_tree"] == _git(root, "rev-parse", "HEAD^{tree}")
    assert len(value["dependency_lock"]) == 64
    assert set(value["memories"]) == {".org-memory/items/policy.md"}
    assert set(value["hooks"]) == {".claude/settings.json", ".codex/hooks.json"}
    assert set(value["governance_checks"]) == {"src/lab/governance/checks/platform.py"}
    assert value["python_version"]
    assert value["platform"]
    assert "pyproject.toml" in value["platform_config"]
    assert verify_baseline(root, runs_root, "platform-v1").name == "platform-v1"

    (root / ".codex" / "hooks.json").write_text('{"tampered": true}\n')
    with pytest.raises(ValueError, match="does not match"):
        verify_baseline(root, runs_root, "platform-v1")


def test_freeze_rejects_dirty_state_and_unsafe_names(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    (root / "untracked.txt").write_text("dirty\n")

    with pytest.raises(ValueError, match="clean Git worktree"):
        freeze_baseline(root, runs_root, "platform-v1")
    for name in ("../escape", "..", "/absolute", "bad/name", ""):
        with pytest.raises(ValueError, match="safe identifier"):
            freeze_baseline(root, runs_root, name)


def test_create_verify_three_resets_and_archive_preserve_external_evidence(
    tmp_path: Path,
) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    unrelated = tmp_path / "unrelated-worktree"
    _git(root, "worktree", "add", "--detach", str(unrelated), "HEAD")

    worktree = create_run(root, runs_root, "run-001", "block")
    run_dir = runs_root / "runs" / "run-001"
    transcript = run_dir / "artifacts" / "transcripts" / "session.jsonl"
    log = run_dir / "artifacts" / "logs" / "client.log"
    transcript.write_text("transcript\n")
    log.write_text("log\n")

    assert worktree.parent == run_dir
    assert _git(worktree, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
    assert verify_run(root, runs_root, "run-001").reset_count == 0

    snapshots = []
    for reset_number in range(1, 4):
        (worktree / "sample_app" / "service.py").write_text(
            f"VALUE = {reset_number + 1}\n", encoding="utf-8"
        )
        reset_run(root, runs_root, "run-001")
        snapshots.append(
            (
                _git(worktree, "rev-parse", "HEAD"),
                (worktree / "sample_app" / "service.py").read_text(),
            )
        )
        assert (run_dir / "artifacts" / "patches" / f"reset-{reset_number:04d}.patch").is_file()
        assert transcript.read_text() == "transcript\n"
        assert log.read_text() == "log\n"
        assert unrelated.is_dir()

    assert snapshots[0] == snapshots[1] == snapshots[2]
    assert verify_run(root, runs_root, "run-001").reset_count == 3

    (worktree / "sample_app" / "service.py").write_text("VALUE = 99\n")
    archive_patch = archive_run(root, runs_root, "run-001")
    archived = RunManifest.from_dict(read_json(run_dir / "run.json"))
    assert archive_patch.name == "archive-0004.patch"
    assert "VALUE = 99" in archive_patch.read_text()
    assert archived.status == "archived"
    assert not worktree.exists()
    assert transcript.is_file() and log.is_file() and unrelated.is_dir()


def test_tampered_baseline_fails_reset_before_named_worktree_is_removed(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    path = freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "audit")
    path.write_text(path.read_text() + " ", encoding="utf-8")

    with pytest.raises(ValueError, match="modified after run creation"):
        reset_run(root, runs_root, "run-001")
    assert worktree.is_dir()


def test_run_rejects_unsafe_ids_and_symlinked_external_root(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    for run_id in ("../escape", "..", "/absolute", "bad/run", ""):
        with pytest.raises(ValueError, match="safe identifier"):
            create_run(root, runs_root, run_id, "audit")

    actual = tmp_path / "actual-runs"
    actual.mkdir()
    linked = tmp_path / "linked-runs"
    linked.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinked ancestor"):
        create_run(root, linked, "run-001", "audit")


def test_cli_wires_baseline_and_run_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, runs_root = _repository(tmp_path)
    monkeypatch.chdir(root)

    assert main(["baseline", "freeze", "--name", "platform-v1"]) == 0
    assert main(["baseline", "verify", "--name", "platform-v1"]) == 0
    assert main(["run", "create", "--id", "run-001", "--mode", "audit"]) == 0
    assert main(["run", "verify", "--id", "run-001"]) == 0
    assert main(["run", "reset", "--id", "run-001"]) == 0
    assert main(["run", "archive", "--id", "run-001"]) == 0
    assert (runs_root / "runs" / "run-001" / "run.json").is_file()
    assert not (runs_root / "runs" / "run-001" / "worktree").exists()


def test_run_manifest_path_tampering_cannot_redirect_reset(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "audit")
    run_path = runs_root / "runs" / "run-001" / "run.json"
    value = json.loads(run_path.read_text())
    value["worktree"] = str(tmp_path / "unrelated")
    run_path.write_text(json.dumps(value))

    with pytest.raises(ValueError, match="paths do not match"):
        reset_run(root, runs_root, "run-001")
    assert worktree.is_dir()


def test_artifact_symlink_cannot_redirect_reset_patch(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "audit")
    patches = runs_root / "runs" / "run-001" / "artifacts" / "patches"
    patches.rmdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    patches.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="must not be a symlink"):
        reset_run(root, runs_root, "run-001")
    assert worktree.is_dir()
    assert list(outside.iterdir()) == []
