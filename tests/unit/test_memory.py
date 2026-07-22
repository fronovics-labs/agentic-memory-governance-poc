from dataclasses import replace

import pytest

from lab.memory.model import Memory, parse_memory, render_memory


def memory() -> Memory:
    return Memory(
        id="ADR-001",
        type="architecture_decision",
        authority="mandatory",
        status="active",
        scopes=["sample_app/application/**"],
        owner="architecture",
        source_ids=["DECISION-42"],
        enforcement_ids=[],
        valid_from="2026-07-22",
        valid_until="",
        supersedes="",
        body="Application services depend on repository interfaces.",
    )


def test_memory_round_trips_every_required_field() -> None:
    item = memory()

    assert parse_memory(render_memory(item)) == item


def test_memory_allows_open_dates_and_empty_references() -> None:
    item = replace(memory(), source_ids=[], valid_from="", valid_until="")

    assert parse_memory(render_memory(item)) == item


def test_memory_rejects_malformed_metadata() -> None:
    with pytest.raises(ValueError):
        replace(memory(), id="../escape")
    with pytest.raises(ValueError):
        replace(memory(), source_ids=["../source"])
    with pytest.raises(ValueError):
        replace(memory(), valid_from="not-a-date")
    with pytest.raises(ValueError):
        replace(memory(), valid_from="2026-07-23", valid_until="2026-07-22")


def test_parser_reports_missing_required_field() -> None:
    text = render_memory(memory()).replace('owner = "architecture"\n', "")

    with pytest.raises(ValueError, match="missing required fields: owner"):
        parse_memory(text)
