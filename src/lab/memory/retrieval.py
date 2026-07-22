"""Deterministic keyword and path-scope memory retrieval."""

import re
from datetime import date
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import PurePosixPath
from typing import Protocol

from lab.memory.model import Memory

_WORD = re.compile(r"[^\W_]+")


class MemoryRepository(Protocol):
    def load_all(self) -> list[Memory]: ...


def search_memories(
    repository: MemoryRepository,
    query: str,
    *,
    path: str | None = None,
    today: date | None = None,
) -> list[Memory]:
    query_terms = _terms(query)
    if not query_terms:
        return []

    current_date = today or date.today()
    current = [
        memory
        for memory in repository.load_all()
        if _is_current(memory, current_date) and _applies_to_path(memory, path)
    ]
    superseded = {memory.supersedes for memory in current if memory.supersedes}
    ranked: list[tuple[int, str, Memory]] = []
    for memory in current:
        if memory.id in superseded:
            continue
        score = len(query_terms & _terms(_searchable_text(memory)))
        if score:
            ranked.append((-score, memory.id, memory))
    return [memory for _, _, memory in sorted(ranked)]


def _terms(text: str) -> set[str]:
    return set(_WORD.findall(text.casefold()))


def _searchable_text(memory: Memory) -> str:
    return " ".join(
        [memory.id, memory.type, memory.authority, memory.owner, *memory.scopes, memory.body]
    )


def _is_current(memory: Memory, today: date) -> bool:
    if memory.status != "active":
        return False
    if memory.valid_from and today < date.fromisoformat(memory.valid_from):
        return False
    return not memory.valid_until or today <= date.fromisoformat(memory.valid_until)


def _applies_to_path(memory: Memory, path: str | None) -> bool:
    return (
        path is None
        or not memory.scopes
        or any(_path_matches(path, scope) for scope in memory.scopes)
    )


def _path_matches(path: str, pattern: str) -> bool:
    path_parts = PurePosixPath(path).parts
    pattern_parts = PurePosixPath(pattern).parts

    @lru_cache(maxsize=None)
    def matches(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)
        if pattern_parts[pattern_index] == "**":
            return matches(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and matches(path_index + 1, pattern_index)
            )
        return (
            path_index < len(path_parts)
            and fnmatchcase(path_parts[path_index], pattern_parts[pattern_index])
            and matches(path_index + 1, pattern_index + 1)
        )

    return matches(0, 0)
