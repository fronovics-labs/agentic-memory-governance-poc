import subprocess
from pathlib import Path

import pytest

from lab.governance.checks import (
    BaselineManifestCheck,
    CompletionCommandsCheck,
    ProtectedPathsCheck,
)
from lab.governance.checks import platform as platform_checks
from lab.governance.model import CheckContext, CommandResult


def test_protected_paths_check_matches_only_repository_root_surfaces() -> None:
    context = CheckContext(
        phase="pre_write",
        changed_paths=(
            ".org-memory/items/ADR-001.md",
            ".claude/settings.json",
            ".codex/hooks.json",
            "src/lab/governance/checks/new.py",
            "vendor/.org-memory/ADR.md",
            "vendor/.claude/settings.json",
            "copy/src/lab/governance/checks/x.py",
            ".org-memory-backup/item.md",
        ),
    )

    assert [violation.path for violation in ProtectedPathsCheck().evaluate(context)] == [
        ".org-memory/items/ADR-001.md",
        ".claude/settings.json",
        ".codex/hooks.json",
        "src/lab/governance/checks/new.py",
    ]


@pytest.mark.parametrize(
    "path",
    ["", "/etc/passwd", "C:/repo/file", r"src\file", "../outside", "src/../../outside"],
)
def test_context_rejects_unsafe_repository_paths(path: str) -> None:
    with pytest.raises(ValueError):
        CheckContext(phase="pre_write", changed_paths=(path,))


def test_baseline_manifest_check_blocks_write_and_detects_hash_mismatch() -> None:
    check = BaselineManifestCheck()
    write = CheckContext(
        phase="pre_write",
        changed_paths=("baseline/platform-v1.json",),
        baseline_manifest_path="baseline/platform-v1.json",
    )
    completion = CheckContext(phase="completion", baseline_manifest_valid=False)

    assert [violation.path for violation in check.evaluate(write)] == ["baseline/platform-v1.json"]
    assert [violation.message for violation in check.evaluate(completion)] == [
        "baseline manifest hash mismatch"
    ]


def test_completion_check_runs_exact_commands_with_configured_bounds() -> None:
    calls: list[tuple[tuple[str, ...], str, float, int]] = []

    def runner(command: tuple[str, ...], cwd: str, timeout: float, limit: int) -> CommandResult:
        calls.append((command, cwd, timeout, limit))
        return CommandResult(command, 0)

    check = CompletionCommandsCheck(runner, timeout_seconds=7, output_limit=11)

    assert check.evaluate(CheckContext(phase="completion", cwd="/workspace")) == []
    assert calls == [
        (command, "/workspace", 7, 11) for command in platform_checks.REQUIRED_COMMANDS
    ]


def test_completion_check_aggregates_failures_and_runs_every_command() -> None:
    calls: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...], cwd: str, timeout: float, limit: int) -> CommandResult:
        del cwd, timeout, limit
        calls.append(command)
        if len(calls) == 1:
            return CommandResult(command, 1, stdout="x" * 20)
        if len(calls) == 2:
            return CommandResult(command, None, error="timed out after 1 second")
        if len(calls) == 3:
            raise OSError("missing executable")
        return CommandResult(command, 0)

    violations = CompletionCommandsCheck(runner, output_limit=5).evaluate(
        CheckContext(phase="completion")
    )

    assert calls == list(platform_checks.REQUIRED_COMMANDS)
    assert len(violations) == 3
    assert "exit code 1" in violations[0].message
    assert "xxxxx...[truncated]" in violations[0].message
    assert "timed out after 1 second" in violations[1].message
    assert "OSError: missing executable" in violations[2].message


def test_default_runner_uses_bounded_shell_free_subprocess(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 1, stdout="abcdef", stderr="uvwxyz")

    monkeypatch.setattr(subprocess, "run", run)
    result = platform_checks._run_command(("tool", "arg"), str(tmp_path), 3, 4)

    assert result == CommandResult(("tool", "arg"), 1, "abcd...[truncated]", "uvwx...[truncated]")
    assert captured == {
        "cwd": str(tmp_path),
        "capture_output": True,
        "text": True,
        "timeout": 3,
        "check": False,
        "shell": False,
    }


def test_default_runner_represents_timeout_and_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(("slow",), 2, output=b"abcdef", stderr=b"timeout")

    monkeypatch.setattr(subprocess, "run", timeout)
    timed_out = platform_checks._run_command(("slow",), ".", 2, 3)

    def missing(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("not found")

    monkeypatch.setattr(subprocess, "run", missing)
    failed = platform_checks._run_command(("missing",), ".", 2, 3)

    assert timed_out == CommandResult(
        ("slow",),
        None,
        "abc...[truncated]",
        "tim...[truncated]",
        "timed out after 2 seconds",
    )
    assert failed == CommandResult(("missing",), None, error="OSError: not found")
