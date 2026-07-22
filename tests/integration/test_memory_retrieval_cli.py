import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from lab.memory.model import Memory
from lab.memory.repository import MarkdownMemoryRepository


def run_lab(
    directory: Path, command: str, text_flag: str, text: str, *extra: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "lab",
            "memory",
            command,
            text_flag,
            text,
            "--directory",
            str(directory),
            *extra,
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def test_search_and_context_commands_filter_rank_and_render(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path)
    active = Memory(
        id="ADR-001",
        type="architecture_decision",
        authority="mandatory",
        status="active",
        scopes=["sample_app/application/**"],
        owner="architecture",
        source_ids=[],
        enforcement_ids=[],
        valid_from="",
        valid_until="",
        supersedes="",
        body="Use repository interfaces for order persistence.",
    )
    repository.save(active)
    repository.save(replace(active, id="ADR-002", status="inactive"))
    repository.save(replace(active, id="ADR-003", scopes=["sample_app/domain/**"]))

    searched = run_lab(tmp_path, "search", "--query", "order persistence")
    contextual = run_lab(
        tmp_path,
        "context",
        "--prompt",
        "change order persistence",
        "--path",
        "sample_app/application/orders.py",
    )
    wrong_path = run_lab(
        tmp_path,
        "context",
        "--prompt",
        "change order persistence",
        "--path",
        "sample_app/infrastructure/sqlite_orders.py",
    )

    assert searched.returncode == contextual.returncode == wrong_path.returncode == 0
    assert searched.stdout == (
        "[ADR-001 | mandatory] Use repository interfaces for order persistence.\n"
        "[ADR-003 | mandatory] Use repository interfaces for order persistence.\n"
    )
    assert contextual.stdout == (
        "[ADR-001 | mandatory] Use repository interfaces for order persistence.\n"
    )
    assert wrong_path.stdout == ""
