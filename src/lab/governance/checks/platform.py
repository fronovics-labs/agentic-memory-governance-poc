"""Checks that protect the experimental platform itself."""

import posixpath
from pathlib import PurePosixPath

from lab.governance.model import CheckContext, CommandResult, Violation


class ProtectedPathsCheck:
    @property
    def id(self) -> str:
        return "platform.protected_paths"

    def evaluate(self, context: CheckContext) -> list[Violation]:
        if context.phase != "pre_write":
            return []
        return [
            Violation(self.id, f"protected platform path: {path}", path)
            for path in context.changed_paths
            if _is_protected(path)
        ]


class BaselineManifestCheck:
    @property
    def id(self) -> str:
        return "platform.baseline_manifest"

    def evaluate(self, context: CheckContext) -> list[Violation]:
        if context.phase == "pre_write" and context.baseline_manifest_path:
            manifest = _parts(context.baseline_manifest_path)
            for path in context.changed_paths:
                if _parts(path) == manifest:
                    return [Violation(self.id, f"baseline manifest is protected: {path}", path)]
        if context.phase == "completion" and not context.baseline_manifest_valid:
            return [Violation(self.id, "baseline manifest hash mismatch")]
        return []


class CompletionCommandsCheck:
    @property
    def id(self) -> str:
        return "platform.completion_commands"

    def evaluate(self, context: CheckContext) -> list[Violation]:
        if context.phase != "completion":
            return []
        passed = {
            name
            for result in context.commands
            if result.exit_code == 0
            for name in [_completed_check(result)]
            if name is not None
        }
        return [
            Violation(self.id, f"required completion check did not pass: {name}")
            for name in ("ruff format", "ruff check", "mypy", "pytest")
            if name not in passed
        ]


def _is_protected(path: str) -> bool:
    parts = _parts(path)
    return (
        ".org-memory" in parts
        or _contains(parts, (".claude", "settings.json"))
        or _contains(parts, (".codex", "hooks.json"))
        or _contains(parts, ("src", "lab", "governance", "checks"))
    )


def _parts(path: str) -> tuple[str, ...]:
    normalized = posixpath.normpath(path.replace("\\", "/"))
    return tuple(part for part in normalized.split("/") if part not in ("", "."))


def _contains(parts: tuple[str, ...], target: tuple[str, ...]) -> bool:
    return any(parts[index : index + len(target)] == target for index in range(len(parts)))


def _completed_check(result: CommandResult) -> str | None:
    command = result.command
    if len(command) >= 3 and PurePosixPath(command[0]).name == "uv" and command[1] == "run":
        command = command[2:]
    tool = PurePosixPath(command[0]).name
    arguments = command[1:]
    if tool == "ruff" and arguments in (("format", "--check", "."), ("format", ".", "--check")):
        return "ruff format"
    if tool == "ruff" and arguments == ("check", "."):
        return "ruff check"
    if tool == "mypy" and not arguments:
        return "mypy"
    if tool == "pytest" and arguments in ((), ("-q",)):
        return "pytest"
    return None
