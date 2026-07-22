"""Disposable-repository coverage for frozen baselines and run worktrees."""

import json
import subprocess
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from lab.cli import main
from lab.runs.baseline import default_runs_root, freeze_baseline, verify_baseline
from lab.runs.launch import Client, LaunchPlan, build_launch_plan, launch_client, public_plan
from lab.runs.manifest import RunManifest, read_json, sha256_file
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
    assert main(["run", "launch", "--id", "run-001", "--client", "codex", "--dry-run"]) == 0
    assert not (runs_root / "runs" / "run-001" / "artifacts" / "clients").exists()
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


def test_launch_plans_use_named_worktree_and_sanitize_inherited_memory(
    tmp_path: Path,
) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    claude_worktree = create_run(root, runs_root, "run-claude", "audit")
    codex_worktree = create_run(root, runs_root, "run-codex", "block")
    inherited = {
        "PATH": "/bin",
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "0",
        "CLAUDE_CONFIG_DIR": "/tmp/inherited-claude",
        "CODEX_HOME": "/tmp/inherited-codex",
        "LAB_GOVERNANCE_MODE": "audit",
    }

    claude = build_launch_plan(
        root,
        runs_root,
        "run-claude",
        "claude",
        arguments=("--print",),
        base_environment=inherited,
    )
    codex = build_launch_plan(
        root,
        runs_root,
        "run-codex",
        "codex",
        base_environment=inherited,
    )

    assert claude.cwd == claude_worktree and claude.argv == ("claude", "--print")
    assert claude.environment["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"
    assert claude.environment["CLAUDE_CONFIG_DIR"] == str(claude.client_home)
    assert "CODEX_HOME" not in claude.environment
    assert codex.cwd == codex_worktree and codex.argv == ("codex",)
    assert codex.environment["CODEX_HOME"] == str(codex.client_home)
    assert "CLAUDE_CONFIG_DIR" not in codex.environment
    assert codex.environment["LAB_GOVERNANCE_MODE"] == "block"
    assert "PATH" not in str(public_plan(codex))
    assert claude.client_home != codex.client_home
    for path in (claude.client_home, codex.client_home):
        assert not path.exists()
        assert not path.is_relative_to(root)
        assert not path.is_relative_to(claude_worktree)


def test_codex_launch_creates_fresh_memory_disabled_home_and_external_record(
    tmp_path: Path,
) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "block")
    plan = build_launch_plan(root, runs_root, "run-001", "codex", base_environment={})
    observed = []

    with pytest.raises(ValueError, match="paths or executable"):
        launch_client(replace(plan, client_home=tmp_path / "redirected-home"), runner=lambda _: 0)

    def fake_runner(received: LaunchPlan) -> int:
        observed.append(received)
        config = tomllib.loads((plan.client_home / "config.toml").read_text())
        assert config["features"]["memories"] is False
        assert config["memories"] == {"use_memories": False, "generate_memories": False}
        assert config["projects"][str(worktree)]["trust_level"] == "trusted"
        assert plan.record_path.is_file()
        return 0

    assert launch_client(plan, runner=fake_runner) == 0
    assert observed == [plan]
    assert plan.record_path.is_file()
    assert not plan.record_path.is_relative_to(root)
    with pytest.raises(ValueError, match="client state already exists"):
        launch_client(plan, runner=fake_runner)


def test_client_homes_are_unique_across_runs(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    create_run(root, runs_root, "run-001", "audit")
    create_run(root, runs_root, "run-002", "audit")
    first = build_launch_plan(root, runs_root, "run-001", "codex", base_environment={})
    second = build_launch_plan(root, runs_root, "run-002", "codex", base_environment={})

    assert first.client_home != second.client_home
    assert launch_client(first, runner=lambda _: 0) == 0
    assert launch_client(second, runner=lambda _: 0) == 0
    assert first.client_home.is_dir() and second.client_home.is_dir()


@pytest.mark.parametrize(
    "key",
    [
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY",
        "CLAUDE_CONFIG_DIR",
        "CODEX_HOME",
        "LAB_GOVERNANCE_MODE",
    ],
)
def test_launch_rejects_controlled_environment_overrides(key: str, tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    create_run(root, runs_root, "run-001", "audit")

    with pytest.raises(ValueError, match="cannot be overridden"):
        build_launch_plan(
            root,
            runs_root,
            "run-001",
            "claude",
            base_environment={},
            environment_overrides={key: "unsafe"},
        )


def test_launch_allows_safe_environment_and_rejects_modified_project_hooks(
    tmp_path: Path,
) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "audit")
    plan = build_launch_plan(
        root,
        runs_root,
        "run-001",
        "claude",
        base_environment={"PATH": "/bin"},
        environment_overrides={"TERM": "xterm-256color"},
    )
    assert plan.environment["PATH"] == "/bin"
    assert plan.environment["TERM"] == "xterm-256color"

    (worktree / ".claude" / "settings.json").write_text('{"hooks": {}}\n')
    with pytest.raises(ValueError, match="does not match"):
        build_launch_plan(root, runs_root, "run-001", "claude", base_environment={})


def test_launch_rejects_symlinked_client_state(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "audit")
    clients = worktree.parent / "artifacts" / "clients"
    clients.mkdir()
    outside = tmp_path / "outside-client-state"
    outside.mkdir()
    (clients / "codex").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="must not be a symlink"):
        build_launch_plan(root, runs_root, "run-001", "codex", base_environment={})


def test_launch_rejects_all_control_plane_argument_forms(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    create_run(root, runs_root, "run-001", "block")
    cases: list[tuple[Client, tuple[str, ...]]] = [
        ("codex", ("-C", "/tmp")),
        ("codex", ("-C/tmp",)),
        ("codex", ("--cd", "/tmp")),
        ("codex", ("--cd=/tmp",)),
        ("codex", ("-c", "features.memories=true")),
        ("codex", ("-cfeatures.memories=true",)),
        ("codex", ("--config", "memories.use_memories=true")),
        ("codex", ("--config=memories.generate_memories=true",)),
        ("codex", ("--enable", "memories")),
        ("codex", ("--enable=memories",)),
        ("codex", ("-p", "unsafe")),
        ("codex", ("--profile=unsafe",)),
        ("claude", ("--settings", "/tmp/settings.json")),
        ("claude", ("--setting-sources=user,project",)),
        ("claude", ("--add-dir", "/tmp")),
        ("claude", ("--continue",)),
    ]
    for client, arguments in cases:
        with pytest.raises(ValueError, match="override controlled launch state"):
            build_launch_plan(
                root,
                runs_root,
                "run-001",
                client,
                arguments=arguments,
                base_environment={},
            )

    safe = build_launch_plan(
        root,
        runs_root,
        "run-001",
        "codex",
        arguments=("--", "describe -C /tmp and -cfeatures.memories=true"),
        base_environment={},
    )
    assert safe.argv[1:] == ("--", "describe -C /tmp and -cfeatures.memories=true")


def test_launch_revalidates_mode_arguments_and_rolls_back_spawn_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    create_run(root, runs_root, "run-001", "block")
    plan = build_launch_plan(root, runs_root, "run-001", "codex", base_environment={})

    downgraded_environment = dict(plan.environment)
    downgraded_environment["LAB_GOVERNANCE_MODE"] = "audit"
    with pytest.raises(ValueError, match="governance mode"):
        launch_client(replace(plan, environment=downgraded_environment), runner=lambda _: 0)
    with pytest.raises(ValueError, match="override controlled launch state"):
        launch_client(replace(plan, argv=("codex", "-C", "/tmp")), runner=lambda _: 0)

    def failed_spawn(received: LaunchPlan) -> int:
        received.stdout_log.write_text("partial stdout\n")
        received.stderr_log.write_text("partial stderr\n")
        raise OSError("client executable is unavailable")

    monkeypatch.setattr("lab.runs.launch._run_subprocess", failed_spawn)
    with pytest.raises(OSError, match="unavailable"):
        launch_client(plan)
    assert not plan.client_home.parent.exists()
    assert not plan.stdout_log.exists() and not plan.stderr_log.exists()

    assert launch_client(plan, runner=lambda _: 0) == 0


def test_verify_rejects_untracked_governed_files(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "audit")
    (worktree / ".org-memory" / "items" / "injected.md").write_text("untracked policy\n")

    with pytest.raises(ValueError, match="does not match"):
        verify_run(root, runs_root, "run-001")


@pytest.mark.parametrize("operation", ["reset", "archive"])
def test_lifecycle_patch_preserves_untracked_files(tmp_path: Path, operation: str) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "audit")
    created = worktree / "sample_app" / "new_evidence.py"
    created.write_text("EVIDENCE = True\n")

    patch = (
        reset_run(root, runs_root, "run-001")
        if operation == "reset"
        else archive_run(root, runs_root, "run-001")
    )
    if operation == "reset":
        patch = runs_root / "runs" / "run-001" / "artifacts" / "patches" / "reset-0001.patch"

    assert "sample_app/new_evidence.py" in Path(patch).read_text()


def test_failed_worktree_removal_does_not_poison_reset_retry(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "audit")
    (worktree / "sample_app" / "service.py").write_text("VALUE = 2\n")
    _git(root, "worktree", "lock", str(worktree))

    with pytest.raises(ValueError):
        reset_run(root, runs_root, "run-001")
    assert worktree.is_dir()
    _git(root, "worktree", "unlock", str(worktree))

    assert reset_run(root, runs_root, "run-001") == worktree


def test_reset_verifies_manifest_contents_before_removing_worktree(tmp_path: Path) -> None:
    root, runs_root = _repository(tmp_path)
    baseline_path = freeze_baseline(root, runs_root, "platform-v1")
    worktree = create_run(root, runs_root, "run-001", "audit")
    service = worktree / "sample_app" / "service.py"
    service.write_text("VALUE = 99\n")

    baseline = read_json(baseline_path)
    baseline["dependency_lock"] = "0" * 64
    baseline_path.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")
    run_path = runs_root / "runs" / "run-001" / "run.json"
    run = read_json(run_path)
    run["baseline_manifest_sha256"] = sha256_file(baseline_path)
    run_path.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n")

    with pytest.raises(ValueError, match="does not match"):
        reset_run(root, runs_root, "run-001")

    assert service.read_text() == "VALUE = 99\n"
