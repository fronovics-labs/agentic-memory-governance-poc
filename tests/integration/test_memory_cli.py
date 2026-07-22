import subprocess
import sys
from pathlib import Path

from lab.memory.model import Memory, render_memory


def test_memory_validate_command_reports_valid_and_malformed_files(tmp_path: Path) -> None:
    valid = Memory(
        id="ADR-001",
        type="architecture_decision",
        authority="mandatory",
        status="active",
        scopes=[],
        owner="architecture",
        source_ids=[],
        enforcement_ids=[],
        valid_from="",
        valid_until="",
        supersedes="",
        body="Use repository interfaces.",
    )
    (tmp_path / "valid.md").write_text(render_memory(valid), encoding="utf-8")

    passed = subprocess.run(
        [sys.executable, "-m", "lab", "memory", "validate", "--directory", str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    (tmp_path / "broken.md").write_text("+++\nid =", encoding="utf-8")
    failed = subprocess.run(
        [sys.executable, "-m", "lab", "memory", "validate", "--directory", str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert passed.returncode == 0
    assert passed.stdout == "valid: 1 memories\n"
    assert failed.returncode == 1
    assert "broken.md: missing closing TOML delimiter" in failed.stderr


def test_memory_validate_command_rejects_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    result = subprocess.run(
        [sys.executable, "-m", "lab", "memory", "validate", "--directory", str(missing)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert result.stderr == f"memory directory does not exist: {missing}\n"
