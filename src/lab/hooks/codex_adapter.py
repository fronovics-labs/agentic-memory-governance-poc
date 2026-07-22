"""Codex hook JSON translation."""

from collections.abc import Mapping
from typing import Any

from lab.hooks._adapter import handle as handle_json
from lab.hooks._adapter import render_hook_output, request_from_json, run
from lab.hooks.core import HookCore


def handle(payload: Mapping[str, Any], core: HookCore) -> dict[str, object]:
    return handle_json(payload, core, translate=request_from_json, render=render_hook_output)


def main() -> int:
    return run(request_from_json, render_hook_output)


if __name__ == "__main__":
    raise SystemExit(main())
