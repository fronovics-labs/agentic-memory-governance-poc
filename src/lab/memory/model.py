"""Memory metadata parsing and deterministic Markdown rendering."""

import json
import re
import tomllib
from dataclasses import dataclass
from datetime import date
from typing import Any

REQUIRED_FIELDS = (
    "id",
    "type",
    "authority",
    "status",
    "scopes",
    "owner",
    "source_ids",
    "enforcement_ids",
    "valid_from",
    "valid_until",
    "supersedes",
)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


@dataclass(frozen=True, slots=True)
class Memory:
    id: str
    type: str
    authority: str
    status: str
    scopes: list[str]
    owner: str
    source_ids: list[str]
    enforcement_ids: list[str]
    valid_from: str
    valid_until: str
    supersedes: str
    body: str

    def __post_init__(self) -> None:
        _require_identifier(self.id, "id")
        for name in ("type", "authority", "status", "owner"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        _require_strings(self.scopes, "scopes")
        _require_identifiers(self.source_ids, "source_ids")
        _require_identifiers(self.enforcement_ids, "enforcement_ids")
        start = _optional_date(self.valid_from, "valid_from")
        end = _optional_date(self.valid_until, "valid_until")
        if start and end and start > end:
            raise ValueError("valid_from must not be after valid_until")
        if not isinstance(self.supersedes, str):
            raise ValueError("supersedes must be a string")
        if self.supersedes:
            _require_identifier(self.supersedes, "supersedes")
        if not isinstance(self.body, str):
            raise ValueError("body must be a string")


def parse_memory(text: str) -> Memory:
    lines = text.splitlines()
    if not lines or lines[0] != "+++":
        raise ValueError("missing opening TOML delimiter")
    try:
        closing = lines.index("+++", 1)
    except ValueError as error:
        raise ValueError("missing closing TOML delimiter") from error

    try:
        metadata: dict[str, Any] = tomllib.loads("\n".join(lines[1:closing]))
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"invalid TOML: {error}") from error

    missing = [field for field in REQUIRED_FIELDS if field not in metadata]
    unknown = sorted(set(metadata) - set(REQUIRED_FIELDS))
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(unknown)}")

    body = "\n".join(lines[closing + 1 :])
    if body.startswith("\n"):
        body = body[1:]
    return Memory(**metadata, body=body.rstrip("\n"))


def render_memory(memory: Memory) -> str:
    def string(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    def strings(values: list[str]) -> str:
        return "[" + ", ".join(string(value) for value in values) + "]"

    metadata = [
        f"id = {string(memory.id)}",
        f"type = {string(memory.type)}",
        f"authority = {string(memory.authority)}",
        f"status = {string(memory.status)}",
        f"scopes = {strings(memory.scopes)}",
        f"owner = {string(memory.owner)}",
        f"source_ids = {strings(memory.source_ids)}",
        f"enforcement_ids = {strings(memory.enforcement_ids)}",
        f"valid_from = {string(memory.valid_from)}",
        f"valid_until = {string(memory.valid_until)}",
        f"supersedes = {string(memory.supersedes)}",
    ]
    return "\n".join(["+++", *metadata, "+++", "", memory.body, ""])


def validate_collection(memories: list[Memory]) -> list[str]:
    errors: list[str] = []
    by_id: dict[str, Memory] = {}
    for memory in sorted(memories, key=lambda item: item.id):
        if memory.id in by_id:
            errors.append(f"duplicate id: {memory.id}")
        else:
            by_id[memory.id] = memory

    for memory in sorted(by_id.values(), key=lambda item: item.id):
        if memory.supersedes and memory.supersedes not in by_id:
            errors.append(f"{memory.id}: supersedes unknown memory {memory.supersedes}")

    states: dict[str, int] = {}
    stack: list[str] = []

    def visit(memory_id: str) -> None:
        states[memory_id] = 1
        stack.append(memory_id)
        target = by_id[memory_id].supersedes
        if target in by_id:
            if states.get(target, 0) == 0:
                visit(target)
            elif states[target] == 1:
                cycle = stack[stack.index(target) :] + [target]
                errors.append(f"supersession cycle: {' -> '.join(cycle)}")
        stack.pop()
        states[memory_id] = 2

    for memory_id in sorted(by_id):
        if states.get(memory_id, 0) == 0:
            visit(memory_id)
    return errors


def _require_identifier(value: object, name: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a safe identifier")


def _require_strings(values: object, name: str) -> list[str]:
    if not isinstance(values, list) or any(
        not isinstance(value, str) or not value for value in values
    ):
        raise ValueError(f"{name} must be a list of non-empty strings")
    return values


def _require_identifiers(values: object, name: str) -> None:
    for value in _require_strings(values, name):
        _require_identifier(value, name)


def _optional_date(value: object, name: str) -> date | None:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO date or empty string")
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO date or empty string") from error
