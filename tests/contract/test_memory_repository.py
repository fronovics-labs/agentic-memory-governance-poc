from pathlib import Path

import pytest

from lab.memory.model import Memory, render_memory
from lab.memory.repository import MarkdownMemoryRepository


def memory(memory_id: str, supersedes: str = "") -> Memory:
    return Memory(
        id=memory_id,
        type="architecture_decision",
        authority="mandatory",
        status="active",
        scopes=[],
        owner="architecture",
        source_ids=[],
        enforcement_ids=[],
        valid_from="",
        valid_until="",
        supersedes=supersedes,
        body=f"Body for {memory_id}",
    )


def test_repository_round_trips_in_deterministic_order(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path)
    repository.save(memory("ADR-002"))
    repository.save(memory("ADR-001"))

    assert repository.load_all() == [memory("ADR-001"), memory("ADR-002")]
    assert repository.validate() == (2, [])


def test_validation_reports_malformed_metadata_and_duplicate_ids(tmp_path: Path) -> None:
    (tmp_path / "broken.md").write_text("not front matter", encoding="utf-8")
    duplicate = render_memory(memory("ADR-001"))
    (tmp_path / "one.md").write_text(duplicate, encoding="utf-8")
    (tmp_path / "two.md").write_text(duplicate, encoding="utf-8")

    count, errors = MarkdownMemoryRepository(tmp_path).validate()

    assert count == 2
    assert any("missing opening TOML delimiter" in error for error in errors)
    assert "duplicate id: ADR-001" in errors


def test_validation_reports_invalid_reference_and_supersession_cycle(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path)
    repository.save(memory("ADR-001", "MISSING"))
    repository.save(memory("ADR-002", "ADR-003"))
    repository.save(memory("ADR-003", "ADR-002"))

    _, errors = repository.validate()

    assert "ADR-001: supersedes unknown memory MISSING" in errors
    assert "supersession cycle: ADR-002 -> ADR-003 -> ADR-002" in errors


def test_repository_rejects_symlinked_memory(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-memory.md"
    outside.write_text(render_memory(memory("ADR-001")), encoding="utf-8")
    (tmp_path / "linked.md").symlink_to(outside)

    count, errors = MarkdownMemoryRepository(tmp_path).validate()

    assert count == 0
    assert errors == [f"unsafe memory path: {tmp_path / 'linked.md'}"]


def test_validation_rejects_missing_root(tmp_path: Path) -> None:
    root = tmp_path / "missing"

    assert MarkdownMemoryRepository(root).validate() == (
        0,
        [f"memory directory does not exist: {root}"],
    )


def test_save_rejects_symlinked_ancestor_without_writing_outside(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    base = tmp_path / "base"
    base.mkdir()
    (base / "link").symlink_to(outside, target_is_directory=True)
    repository = MarkdownMemoryRepository(base / "link" / "nested-items")

    with pytest.raises(ValueError, match="symlinked ancestor"):
        repository.save(memory("ADR-001"))

    assert not (outside / "nested-items").exists()


def test_load_rejects_symlinked_ancestor(tmp_path: Path) -> None:
    outside = tmp_path / "outside" / "nested-items"
    outside.mkdir(parents=True)
    (outside / "ADR-001.md").write_text(render_memory(memory("ADR-001")), encoding="utf-8")
    base = tmp_path / "base"
    base.mkdir()
    (base / "link").symlink_to(outside.parent, target_is_directory=True)
    repository = MarkdownMemoryRepository(base / "link" / "nested-items")

    with pytest.raises(ValueError, match="symlinked ancestor"):
        repository.load_all()
