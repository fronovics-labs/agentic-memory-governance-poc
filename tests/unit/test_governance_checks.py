from lab.governance.checks import (
    BaselineManifestCheck,
    CompletionCommandsCheck,
    ProtectedPathsCheck,
)
from lab.governance.model import CheckContext, CommandResult


def test_protected_paths_check_blocks_only_platform_paths() -> None:
    context = CheckContext(
        phase="pre_write",
        changed_paths=(
            ".org-memory/items/ADR-001.md",
            "work/../.claude/settings.json",
            r".codex\hooks.json",
            "src/lab/governance/checks/new.py",
            ".org-memory-backup/item.md",
            ".claude/notes.md",
            "src/lab/governance/model.py",
        ),
    )

    assert [violation.path for violation in ProtectedPathsCheck().evaluate(context)] == [
        ".org-memory/items/ADR-001.md",
        "work/../.claude/settings.json",
        r".codex\hooks.json",
        "src/lab/governance/checks/new.py",
    ]


def test_baseline_manifest_check_blocks_write_and_detects_hash_mismatch() -> None:
    check = BaselineManifestCheck()
    write = CheckContext(
        phase="pre_write",
        changed_paths=("runs/../baseline/platform-v1.json",),
        baseline_manifest_path="baseline/platform-v1.json",
    )
    completion = CheckContext(phase="completion", baseline_manifest_valid=False)

    assert [violation.path for violation in check.evaluate(write)] == [
        "runs/../baseline/platform-v1.json"
    ]
    assert [violation.message for violation in check.evaluate(completion)] == [
        "baseline manifest hash mismatch"
    ]


def test_completion_commands_check_requires_successful_full_gates() -> None:
    check = CompletionCommandsCheck()
    complete = CheckContext(
        phase="completion",
        commands=(
            CommandResult(("uv", "run", "ruff", "format", "--check", "."), 0),
            CommandResult(("uv", "run", "ruff", "check", "."), 0),
            CommandResult(("uv", "run", "mypy"), 0),
            CommandResult(("uv", "run", "pytest", "-q"), 0),
        ),
    )

    assert check.evaluate(complete) == []


def test_completion_commands_check_rejects_failed_or_partial_gates() -> None:
    context = CheckContext(
        phase="completion",
        commands=(
            CommandResult(("ruff", "format", "--check", "src"), 0),
            CommandResult(("ruff", "check", "."), 1),
            CommandResult(("mypy", "src"), 0),
            CommandResult(("pytest", "--ignore=tests"), 0),
        ),
    )

    assert [violation.message for violation in CompletionCommandsCheck().evaluate(context)] == [
        "required completion check did not pass: ruff format",
        "required completion check did not pass: ruff check",
        "required completion check did not pass: mypy",
        "required completion check did not pass: pytest",
    ]
