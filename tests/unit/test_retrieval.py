from dataclasses import replace
from datetime import date

from lab.memory.model import Memory
from lab.memory.renderer import render_context
from lab.memory.retrieval import search_memories

TODAY = date(2026, 7, 22)


class Memories:
    def __init__(self, *items: Memory) -> None:
        self.items = list(items)

    def load_all(self) -> list[Memory]:
        return self.items


def memory(memory_id: str, body: str = "Change order persistence") -> Memory:
    return Memory(
        id=memory_id,
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
        body=body,
    )


def search(*items: Memory, query: str = "order persistence", path: str | None = None) -> list[str]:
    return [item.id for item in search_memories(Memories(*items), query, path=path, today=TODAY)]


def test_retrieval_filters_inapplicable_memories() -> None:
    active = memory("ACTIVE")
    inactive = replace(memory("INACTIVE"), status="inactive")
    future = replace(memory("FUTURE"), valid_from="2026-07-23")
    expired = replace(memory("EXPIRED"), valid_until="2026-07-21")
    old = memory("OLD")
    successor = replace(memory("NEW"), supersedes="OLD")
    wrong_scope = replace(memory("WRONG-SCOPE"), scopes=["sample_app/domain/**"])

    assert search(
        active,
        inactive,
        future,
        expired,
        old,
        successor,
        wrong_scope,
        path="sample_app/application/orders.py",
    ) == ["ACTIVE", "NEW"]


def test_retrieval_accepts_inclusive_dates_global_scope_and_inactive_successor() -> None:
    bounded = replace(memory("BOUNDED"), valid_from="2026-07-22", valid_until="2026-07-22")
    global_memory = replace(memory("GLOBAL"), scopes=[])
    old = memory("OLD")
    inactive_successor = replace(memory("NEW"), status="inactive", supersedes="OLD")

    assert search(
        bounded,
        global_memory,
        old,
        inactive_successor,
        path="sample_app/application/orders.py",
    ) == ["BOUNDED", "GLOBAL", "OLD"]


def test_wrong_scope_successor_does_not_hide_applicable_memory() -> None:
    old = memory("OLD")
    wrong_scope_successor = replace(
        memory("NEW"), supersedes="OLD", scopes=["sample_app/domain/**"]
    )

    assert search(
        old,
        wrong_scope_successor,
        path="sample_app/application/orders.py",
    ) == ["OLD"]


def test_retrieval_uses_whole_keywords_and_stable_ranking() -> None:
    strongest = memory("B", "Order persistence repository")
    tie_first = memory("A", "Order only")
    tie_second = memory("D", "Order only")
    nearby = memory("C", "Ordering persists")

    assert search(strongest, tie_first, nearby, query="order persistence repository") == ["B", "A"]
    assert search(tie_second, tie_first, query="order") == ["A", "D"]
    assert search(nearby, query="order") == []
    assert search(memory("UNICODE", "Résumé policy"), query="résumé") == ["UNICODE"]


def test_scope_globs_respect_segment_boundaries_and_recursive_wildcards() -> None:
    one_segment = replace(memory("ONE"), scopes=["sample_app/application/*"])
    recursive = replace(memory("RECURSIVE"), scopes=["sample_app/application/**"])
    middle_recursive = replace(memory("MIDDLE"), scopes=["sample_app/**/orders.py"])

    nested = "sample_app/application/nested/orders.py"
    assert search(one_segment, recursive, middle_recursive, path=nested) == ["MIDDLE", "RECURSIVE"]
    assert search(one_segment, path="sample_app/application/orders.py") == ["ONE"]
    assert search(recursive, path="sample_app/app/orders.py") == []


def test_renderer_is_concise_and_stable() -> None:
    first = memory("ADR-001", "Use   repository\ninterfaces.")
    second = replace(memory("ADR-002", "Keep SQLite at the edge."), authority="advisory")

    assert render_context([first, second]) == (
        "[ADR-001 | mandatory] Use repository interfaces.\n"
        "[ADR-002 | advisory] Keep SQLite at the edge."
    )
