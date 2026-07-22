"""Checks that protect the experimental platform itself."""

import shlex
import subprocess
from collections.abc import Callable

from lab.governance.model import CheckContext, CommandResult, Violation

Runner = Callable[[tuple[str, ...], str, float, int], CommandResult]
REQUIRED_COMMANDS = (
    ("uv", "run", "ruff", "format", "--check", "."),
    ("uv", "run", "ruff", "check", "."),
    ("uv", "run", "mypy"),
    ("uv", "run", "pytest", "-q"),
)


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
    def __init__(
        self,
        runner: Runner | None = None,
        *,
        timeout_seconds: float = 120,
        output_limit: int = 4000,
    ) -> None:
        if timeout_seconds <= 0 or output_limit <= 0:
            raise ValueError("timeout and output limit must be positive")
        self._runner = runner or _run_command
        self._timeout_seconds = timeout_seconds
        self._output_limit = output_limit

    @property
    def id(self) -> str:
        return "platform.completion_commands"

    def evaluate(self, context: CheckContext) -> list[Violation]:
        if context.phase != "completion":
            return []
        violations: list[Violation] = []
        for command in REQUIRED_COMMANDS:
            try:
                result = self._runner(
                    command,
                    context.cwd,
                    self._timeout_seconds,
                    self._output_limit,
                )
                if result.command != command:
                    raise ValueError("runner returned a result for a different command")
            except Exception as error:
                violations.append(
                    Violation(
                        self.id,
                        f"completion command could not run: {shlex.join(command)}: "
                        f"{type(error).__name__}: {error}",
                    )
                )
                continue
            if result.exit_code != 0 or result.error:
                details = result.error or f"exit code {result.exit_code}"
                output = _result_output(result, self._output_limit)
                violations.append(
                    Violation(
                        self.id,
                        f"completion command failed: {shlex.join(command)}: {details}{output}",
                    )
                )
        return violations


def _is_protected(path: str) -> bool:
    parts = tuple(path.split("/"))
    return (
        parts[0] == ".org-memory"
        or parts[:2] == (".claude", "settings.json")
        or parts[:2] == (".codex", "hooks.json")
        or parts[:4] == ("src", "lab", "governance", "checks")
    )


def _parts(path: str) -> tuple[str, ...]:
    return tuple(path.split("/"))


def _run_command(
    command: tuple[str, ...], cwd: str, timeout_seconds: float, output_limit: int
) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
        return CommandResult(
            command,
            completed.returncode,
            _bounded(completed.stdout, output_limit),
            _bounded(completed.stderr, output_limit),
        )
    except subprocess.TimeoutExpired as error:
        return CommandResult(
            command,
            None,
            _bounded(_text(error.stdout), output_limit),
            _bounded(_text(error.stderr), output_limit),
            f"timed out after {timeout_seconds:g} seconds",
        )
    except OSError as error:
        return CommandResult(command, None, error=f"{type(error).__name__}: {error}")


def _result_output(result: CommandResult, limit: int) -> str:
    parts = []
    if result.stdout:
        parts.append(f"stdout={_bounded(result.stdout, limit)!r}")
    if result.stderr:
        parts.append(f"stderr={_bounded(result.stderr, limit)!r}")
    return "" if not parts else "; " + "; ".join(parts)


def _bounded(output: str, limit: int) -> str:
    return output if len(output) <= limit else output[:limit] + "...[truncated]"


def _text(output: str | bytes | None) -> str:
    return output.decode(errors="replace") if isinstance(output, bytes) else output or ""
