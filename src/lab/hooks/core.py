"""Client-neutral lifecycle hook behavior."""

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from lab.governance.checks.platform import (
    BaselineManifestCheck,
    CompletionCommandsCheck,
    ProtectedPathsCheck,
)
from lab.governance.engine import GovernanceEngine
from lab.governance.model import CheckContext, GovernanceMode, Violation
from lab.memory.renderer import render_context
from lab.memory.repository import MarkdownMemoryRepository
from lab.memory.retrieval import MemoryRepository, search_memories

HookEvent = Literal["UserPromptSubmit", "PreToolUse", "Stop"]
_PATCH_PATH = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)
_COMMAND_PATH = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)")
_SHELL_SEPARATORS = {";", "&&", "||", "|", "&"}
_READ_ONLY_COMMANDS = {
    "cat",
    "diff",
    "echo",
    "find",
    "grep",
    "head",
    "ls",
    "pwd",
    "rg",
    "stat",
    "tail",
    "wc",
}


@dataclass(frozen=True, slots=True)
class HookRequest:
    event: HookEvent
    prompt: str = ""
    tool_name: str = ""
    tool_input: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class HookOutcome:
    allowed: bool = True
    additional_context: str = ""
    violations: tuple[Violation, ...] = ()


class HookCore:
    def __init__(
        self,
        memory_repository: MemoryRepository,
        governance: GovernanceEngine,
        *,
        root: str | Path,
        mode: GovernanceMode,
        baseline_manifest_path: str | None = None,
        baseline_manifest_valid: bool = True,
    ) -> None:
        if mode not in ("audit", "block"):
            raise ValueError(f"unsupported governance mode: {mode}")
        self._memory_repository = memory_repository
        self._governance = governance
        self._root = Path(root).resolve()
        self._mode = mode
        self._baseline_manifest_path = baseline_manifest_path
        self._baseline_manifest_valid = baseline_manifest_valid

    def handle(self, request: HookRequest) -> HookOutcome:
        if request.event == "UserPromptSubmit":
            memories = search_memories(self._memory_repository, request.prompt)
            return HookOutcome(additional_context=render_context(memories))
        if request.event == "PreToolUse":
            tool_input = request.tool_input or {}
            paths = _changed_paths(request.tool_name, tool_input, self._root)
            result = self._governance.evaluate(
                CheckContext(
                    phase="pre_write",
                    changed_paths=paths,
                    baseline_manifest_path=self._baseline_manifest_path,
                    cwd=str(self._root),
                ),
                "block",
            )
            violations = list(result.violations)
            command = tool_input.get("command")
            if isinstance(command, str) and _is_destructive(command):
                violations.append(
                    Violation(
                        "hook.destructive_command",
                        "destructive reset or baseline command is not allowed inside a run",
                    )
                )
            return HookOutcome(allowed=not violations, violations=tuple(violations))

        result = self._governance.evaluate(
            CheckContext(
                phase="completion",
                baseline_manifest_path=self._baseline_manifest_path,
                baseline_manifest_valid=self._baseline_manifest_valid,
                cwd=str(self._root),
            ),
            self._mode,
        )
        return HookOutcome(allowed=result.allowed, violations=result.violations)


def default_core(root: str | Path, mode: GovernanceMode) -> HookCore:
    repository_root = Path(root).resolve()
    return HookCore(
        MarkdownMemoryRepository(repository_root / ".org-memory" / "items"),
        GovernanceEngine(
            [ProtectedPathsCheck(), BaselineManifestCheck(), CompletionCommandsCheck()]
        ),
        root=repository_root,
        mode=mode,
    )


def format_violations(violations: tuple[Violation, ...]) -> str:
    return "\n".join(
        f"[{violation.check_id}] {violation.message}"
        + (f" ({violation.path})" if violation.path else "")
        for violation in violations
    )


def _changed_paths(tool_name: str, tool_input: Mapping[str, Any], root: Path) -> tuple[str, ...]:
    candidates: list[str] = []
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            candidates.append(value)
    command = tool_input.get("command")
    if isinstance(command, str):
        candidates.extend(_PATCH_PATH.findall(command))
        candidates.extend(_shell_write_paths(command))
        candidates.extend(_unsafe_command_path_mentions(command))

    normalized = {_repository_path(candidate, root) for candidate in candidates}
    return tuple(sorted(path for path in normalized if path is not None))


def _repository_path(path: str, root: Path) -> str | None:
    candidate = Path(path)
    if "\\" in path:
        return None
    try:
        resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return None


def _shell_write_paths(command: str) -> list[str]:
    paths: list[str] = []
    for segment in _shell_segments(command):
        if not segment:
            continue
        for index, token in enumerate(segment[:-1]):
            if token in (">", ">>"):
                paths.append(segment[index + 1])
        executable = Path(segment[0]).name
        if executable in {"touch", "rm", "mkdir", "rmdir", "truncate", "tee"}:
            paths.extend(token for token in segment[1:] if not token.startswith("-"))
        elif executable in {"cp", "mv", "install"}:
            paths.extend(token for token in segment[1:] if not token.startswith("-"))
        elif executable == "sed" and any(
            token == "-i" or token.startswith("-i") for token in segment
        ):
            paths.extend(token for token in segment[1:] if not token.startswith("-"))
    return paths


def _is_destructive(command: str) -> bool:
    for segment in _shell_segments(command):
        words = _command_words(segment)
        if words[:2] == ["git", "reset"]:
            return True
        if words[:3] in (["lab", "baseline", "freeze"], ["lab", "run", "reset"]):
            return True
        if words and words[0] in {"bash", "sh", "zsh"} and "-c" in words:
            index = words.index("-c")
            if index + 1 < len(words) and _is_destructive(words[index + 1]):
                return True
    return False


def _command_words(segment: list[str]) -> list[str]:
    words = list(segment)
    while words and "=" in words[0] and not words[0].startswith(("/", "./")):
        words.pop(0)
    if words and Path(words[0]).name in {"command", "env"}:
        words = words[1:]
        while words and (words[0].startswith("-") or "=" in words[0]):
            words.pop(0)
    if words[:2] == ["uv", "run"]:
        words = words[2:]
        while words and words[0].startswith("-"):
            words.pop(0)
    if len(words) >= 3 and Path(words[0]).name.startswith("python") and words[1:3] == ["-m", "lab"]:
        words = ["lab", *words[3:]]
    if words:
        words[0] = Path(words[0]).name
    return words


def _unsafe_command_path_mentions(command: str) -> list[str]:
    paths: list[str] = []
    for segment in _shell_segments(command):
        words = _command_words(segment)
        if _is_read_only(words):
            continue
        paths.extend(_COMMAND_PATH.findall(" ".join(segment)))
    return paths


def _is_read_only(words: list[str]) -> bool:
    if not words:
        return True
    if words[0] in _READ_ONLY_COMMANDS:
        return True
    if words[0] == "git" and len(words) > 1 and words[1] in {"diff", "log", "show", "status"}:
        return True
    return words[:3] == ["python", "-m", "json.tool"] or words[:3] == [
        "python3",
        "-m",
        "json.tool",
    ]


def _shell_segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in _SHELL_SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return segments
