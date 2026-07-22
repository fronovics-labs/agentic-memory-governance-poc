"""Shared JSON boundary helpers for lifecycle-hook adapters."""

import json
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from lab.governance.model import GovernanceMode
from lab.hooks.core import HookCore, HookOutcome, HookRequest, default_core, format_violations

Translator = Callable[[Mapping[str, Any]], HookRequest]
Renderer = Callable[[HookRequest, HookOutcome], dict[str, object]]


def request_from_json(payload: Mapping[str, Any]) -> HookRequest:
    event = _string(payload, "hook_event_name")
    if event == "UserPromptSubmit":
        return HookRequest(event="UserPromptSubmit", prompt=_string(payload, "prompt"))
    if event == "PreToolUse":
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict) or any(not isinstance(key, str) for key in tool_input):
            raise ValueError("tool_input must be a JSON object")
        return HookRequest(
            event="PreToolUse",
            tool_name=_string(payload, "tool_name"),
            tool_input=tool_input,
        )
    if event == "Stop":
        return HookRequest(event="Stop")
    raise ValueError(f"unsupported hook_event_name: {event}")


def render_hook_output(request: HookRequest, outcome: HookOutcome) -> dict[str, object]:
    if request.event == "UserPromptSubmit":
        return {
            "hookSpecificOutput": {
                "hookEventName": request.event,
                "additionalContext": outcome.additional_context,
            }
        }
    if request.event == "PreToolUse":
        specific: dict[str, object] = {
            "hookEventName": request.event,
            "permissionDecision": "allow" if outcome.allowed else "deny",
        }
        if not outcome.allowed:
            specific["permissionDecisionReason"] = format_violations(outcome.violations)
        return {"hookSpecificOutput": specific}
    if outcome.allowed:
        output: dict[str, object] = {"continue": True}
        if outcome.violations:
            output["systemMessage"] = format_violations(outcome.violations)
        return output
    return {"decision": "block", "reason": format_violations(outcome.violations)}


def handle(
    payload: Mapping[str, Any],
    core: HookCore,
    *,
    translate: Translator,
    render: Renderer,
) -> dict[str, object]:
    request = translate(payload)
    return render(request, core.handle(request))


def run(translate: Translator, render: Renderer) -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("hook input must be a JSON object")
        root = _repository_root(_string(payload, "cwd"))
        mode = _mode(os.environ.get("LAB_GOVERNANCE_MODE", "block"))
        core = default_core(root, mode)
        output = handle(payload, core, translate=translate, render=render)
        message = output.get("systemMessage")
        if isinstance(message, str):
            print(message, file=sys.stderr)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        output = {"continue": False, "stopReason": f"invalid hook input: {error}"}
    json.dump(output, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _mode(value: str) -> GovernanceMode:
    if value == "audit":
        return "audit"
    if value == "block":
        return "block"
    raise ValueError(f"unsupported governance mode: {value}")


def _repository_root(cwd: str) -> Path:
    current = Path(cwd).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ValueError(f"cwd is not inside a Git repository: {cwd}")
