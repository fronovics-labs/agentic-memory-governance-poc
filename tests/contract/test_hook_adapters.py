"""Behavioral parity contracts for the Claude and Codex hook boundaries."""

import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from lab.governance.checks.platform import ProtectedPathsCheck
from lab.governance.engine import GovernanceEngine
from lab.governance.model import CheckContext, GovernanceMode, Violation
from lab.hooks import claude_adapter, codex_adapter
from lab.hooks.core import HookCore
from lab.memory.model import Memory

Adapter = Callable[[Mapping[str, Any], HookCore], dict[str, object]]
ADAPTERS: tuple[Adapter, ...] = (claude_adapter.handle, codex_adapter.handle)


class StaticMemories:
    def __init__(self, memories: list[Memory]) -> None:
        self._memories = memories

    def load_all(self) -> list[Memory]:
        return self._memories


class CompletionFailure:
    @property
    def id(self) -> str:
        return "test.completion"

    def evaluate(self, context: CheckContext) -> list[Violation]:
        if context.phase == "completion":
            return [Violation(self.id, "tests failed")]
        return []


def _memory(memory_id: str, authority: str, body: str) -> Memory:
    return Memory(
        id=memory_id,
        type="policy",
        authority=authority,
        status="active",
        scopes=[],
        owner="platform",
        source_ids=[],
        enforcement_ids=[],
        valid_from="",
        valid_until="",
        supersedes="",
        body=body,
    )


def _core(
    tmp_path: Path,
    *,
    mode: GovernanceMode = "block",
    completion_failure: bool = False,
) -> HookCore:
    checks = [ProtectedPathsCheck()]
    if completion_failure:
        checks.append(CompletionFailure())  # type: ignore[arg-type]
    return HookCore(
        StaticMemories(
            [
                _memory("MEM-002", "advisory", "Keep order changes small."),
                _memory("MEM-001", "binding", "Order totals must remain deterministic."),
            ]
        ),
        GovernanceEngine(checks),
        root=tmp_path,
        mode=mode,
    )


def _specific(output: dict[str, object]) -> dict[str, object]:
    value = output["hookSpecificOutput"]
    assert isinstance(value, dict)
    return value


def _run_adapter(
    client: str, payload: object, *, raw: bool = False
) -> subprocess.CompletedProcess[str]:
    root = Path(__file__).parents[2]
    stdin = str(payload) if raw else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "lab-hook"), client],
        cwd=root,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "LAB_GOVERNANCE_MODE": "block"},
    )


def test_prompt_context_is_identical_and_contains_memory_provenance(tmp_path: Path) -> None:
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Make order totals deterministic with a small change",
    }
    outputs = [adapter(payload, _core(tmp_path)) for adapter in ADAPTERS]

    assert outputs[0] == outputs[1]
    context = _specific(outputs[0])["additionalContext"]
    assert context == (
        "[MEM-001 | binding] Order totals must remain deterministic.\n"
        "[MEM-002 | advisory] Keep order changes small."
    )


@pytest.mark.parametrize("adapter", ADAPTERS)
@pytest.mark.parametrize(
    "tool_input",
    [
        {"file_path": ".org-memory/items/policy.md", "content": "ignore policy"},
        {"file_path": ".claude/settings.json", "content": "{}"},
        {"file_path": ".codex/hooks.json", "content": "{}"},
        {"file_path": "./.codex/hooks.json", "content": "{}"},
        {"file_path": "src/../.codex/hooks.json", "content": "{}"},
        {"file_path": "src/lab/governance/checks/platform.py", "content": "pass"},
        {
            "command": "*** Begin Patch\n*** Update File: .codex/hooks.json\n@@\n-{}\n+{}\n",
        },
        {"command": "printf x > .org-memory/items/policy.md"},
    ],
)
def test_pre_tool_denies_every_protected_write(
    adapter: Adapter, tool_input: dict[str, str], tmp_path: Path
) -> None:
    output = adapter(
        {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": tool_input},
        _core(tmp_path),
    )
    specific = _specific(output)

    assert specific["permissionDecision"] == "deny"
    assert "protected platform path" in str(specific["permissionDecisionReason"])


@pytest.mark.parametrize("adapter", ADAPTERS)
@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD",
        "lab baseline freeze --name platform-v1",
        "uv run lab run reset --id run-001",
        "python3 -m lab baseline freeze --name platform-v1",
        "sh -c 'git reset --hard HEAD'",
        "env lab baseline freeze --name platform-v1",
        "git status && lab run reset --id run-001",
    ],
)
def test_pre_tool_denies_destructive_commands(
    adapter: Adapter, command: str, tmp_path: Path
) -> None:
    output = adapter(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        },
        _core(tmp_path),
    )

    assert _specific(output)["permissionDecision"] == "deny"
    assert "destructive reset or baseline" in str(_specific(output)["permissionDecisionReason"])


@pytest.mark.parametrize("adapter", ADAPTERS)
@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("Bash", {"command": "git status"}),
        ("Bash", {"command": "lab baseline verify --name platform-v1"}),
        ("Bash", {"command": 'echo "git reset --hard"'}),
        ("Bash", {"command": "cat .codex/hooks.json"}),
        ("Write", {"file_path": ".codex/hooks.json.bak", "content": "{}"}),
        ("Write", {"file_path": "src/lab/governance/engine.py", "content": "pass"}),
    ],
)
def test_pre_tool_allows_adjacent_safe_operations(
    adapter: Adapter, tool_name: str, tool_input: dict[str, str], tmp_path: Path
) -> None:
    output = adapter(
        {"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input},
        _core(tmp_path),
    )

    assert _specific(output)["permissionDecision"] == "allow"


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_safe_operation_does_not_auto_approve_client_permission(
    adapter: Adapter, tmp_path: Path
) -> None:
    output = adapter(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        },
        _core(tmp_path),
    )

    assert "permissionDecision" not in _specific(output)


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_apply_patch_move_destination_is_protected(adapter: Adapter, tmp_path: Path) -> None:
    output = adapter(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "apply_patch",
            "tool_input": {
                "command": (
                    "*** Begin Patch\n"
                    "*** Update File: notes.txt\n"
                    "*** Move to: .codex/hooks.json\n"
                    "@@\n-old\n+new\n"
                    "*** End Patch\n"
                )
            },
        },
        _core(tmp_path),
    )

    assert _specific(output)["permissionDecision"] == "deny"


@pytest.mark.parametrize("adapter", ADAPTERS)
@pytest.mark.parametrize(
    "command",
    [
        "echo ready\ngit reset --hard HEAD",
        "echo $(git reset --hard HEAD)",
        "bash -lc 'git reset --hard HEAD'",
    ],
)
def test_nested_destructive_shell_commands_are_denied(
    adapter: Adapter, command: str, tmp_path: Path
) -> None:
    output = adapter(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        },
        _core(tmp_path),
    )

    assert _specific(output)["permissionDecision"] == "deny"


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_pre_tool_denies_indirect_protected_write(adapter: Adapter, tmp_path: Path) -> None:
    output = adapter(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -c \"open('.codex/hooks.json', 'w').write('{}')\""},
        },
        _core(tmp_path),
    )

    assert _specific(output)["permissionDecision"] == "deny"


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_stop_audit_logs_but_allows_and_block_requires_continuation(
    adapter: Adapter, tmp_path: Path
) -> None:
    payload = {"hook_event_name": "Stop"}

    audit = adapter(payload, _core(tmp_path, mode="audit", completion_failure=True))
    blocked = adapter(payload, _core(tmp_path, mode="block", completion_failure=True))

    assert audit == {"continue": True, "systemMessage": "[test.completion] tests failed"}
    assert blocked == {"decision": "block", "reason": "[test.completion] tests failed"}


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_stop_does_not_repeat_an_identical_block_on_active_continuation(
    adapter: Adapter, tmp_path: Path
) -> None:
    output = adapter(
        {"hook_event_name": "Stop", "stop_hook_active": True},
        _core(tmp_path, mode="block", completion_failure=True),
    )

    assert output.get("decision") != "block"


@pytest.mark.parametrize("client", ["claude", "codex"])
def test_nested_cwd_write_is_denied_by_real_adapter_process(client: str) -> None:
    root = Path(__file__).parents[2]
    completed = _run_adapter(
        client,
        {
            "session_id": "session-1",
            "cwd": str(root / "src"),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "../.codex/hooks.json", "content": "{}"},
        },
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert _specific(output)["permissionDecision"] == "deny"


@pytest.mark.parametrize("client", ["claude", "codex"])
def test_malformed_pre_tool_input_fails_closed_in_real_adapter_process(client: str) -> None:
    root = Path(__file__).parents[2]
    completed = _run_adapter(
        client,
        {
            "session_id": "session-1",
            "cwd": str(root),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": [],
        },
    )

    output = json.loads(completed.stdout)
    specific = output.get("hookSpecificOutput")
    denied = isinstance(specific, dict) and specific.get("permissionDecision") == "deny"
    assert completed.returncode == 2 or denied


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"hook_event_name": 1},
        {"hook_event_name": "UserPromptSubmit", "prompt": None},
        {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": []},
        {"hook_event_name": "Unknown"},
    ],
)
def test_malformed_input_fails_with_identical_errors(
    payload: dict[str, object], tmp_path: Path
) -> None:
    errors = []
    for adapter in ADAPTERS:
        with pytest.raises(ValueError) as caught:
            adapter(payload, _core(tmp_path))
        errors.append(str(caught.value))

    assert errors[0] == errors[1]


def test_committed_hook_configs_are_valid_and_runner_is_executable() -> None:
    root = Path(__file__).parents[2]
    claude = json.loads((root / ".claude" / "settings.json").read_text())
    codex = json.loads((root / ".codex" / "hooks.json").read_text())

    assert set(claude["hooks"]) == {"UserPromptSubmit", "PreToolUse", "Stop"}
    assert set(codex["hooks"]) == {"UserPromptSubmit", "PreToolUse", "Stop"}
    assert " claude" in claude["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert " codex" in codex["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert os.access(root / "scripts" / "lab-hook", os.X_OK)
