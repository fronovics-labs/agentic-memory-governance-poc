"""Concise, stable memory context rendering."""

from lab.memory.model import Memory


def render_context(memories: list[Memory]) -> str:
    return "\n".join(
        f"[{memory.id} | {memory.authority}] {' '.join(memory.body.split())}" for memory in memories
    )
