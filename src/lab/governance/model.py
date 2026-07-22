"""Governance check and evaluation contracts."""

import re
from dataclasses import dataclass
from typing import Literal, Protocol

GovernanceMode = Literal["audit", "block"]
GovernancePhase = Literal["pre_write", "completion"]
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None

    def __post_init__(self) -> None:
        if not self.command:
            raise ValueError("command must not be empty")
        if not isinstance(self.stdout, str) or not isinstance(self.stderr, str):
            raise ValueError("command output must be text")


@dataclass(frozen=True, slots=True)
class CheckContext:
    phase: GovernancePhase
    changed_paths: tuple[str, ...] = ()
    baseline_manifest_path: str | None = None
    baseline_manifest_valid: bool = True
    cwd: str = "."

    def __post_init__(self) -> None:
        if self.phase not in ("pre_write", "completion"):
            raise ValueError(f"unsupported governance phase: {self.phase}")
        object.__setattr__(
            self,
            "changed_paths",
            tuple(canonical_repository_path(path) for path in self.changed_paths),
        )
        if self.baseline_manifest_path is not None:
            object.__setattr__(
                self,
                "baseline_manifest_path",
                canonical_repository_path(self.baseline_manifest_path),
            )
        if not isinstance(self.cwd, str) or not self.cwd:
            raise ValueError("cwd must be a non-empty string")


@dataclass(frozen=True, slots=True)
class Violation:
    check_id: str
    message: str
    path: str | None = None

    def __post_init__(self) -> None:
        validate_check_id(self.check_id)
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("violation message must be a non-empty string")
        if self.path is not None and not isinstance(self.path, str):
            raise ValueError("violation path must be a string or None")


class GovernanceCheck(Protocol):
    @property
    def id(self) -> str: ...

    def evaluate(self, context: CheckContext) -> list[Violation]: ...


@dataclass(frozen=True, slots=True)
class GovernanceResult:
    mode: GovernanceMode
    violations: tuple[Violation, ...]
    allowed: bool


def validate_check_id(check_id: object) -> str:
    if not isinstance(check_id, str) or not _SAFE_ID.fullmatch(check_id):
        raise ValueError("governance check ID must be a nonblank safe identifier")
    return check_id


def canonical_repository_path(path: object) -> str:
    if not isinstance(path, str) or not path:
        raise ValueError("repository path must be a non-empty relative POSIX path")
    parts = path.split("/")
    if (
        path.startswith("/")
        or "\\" in path
        or any(part in ("", ".", "..") for part in parts)
        or re.fullmatch(r"[A-Za-z]:", parts[0])
    ):
        raise ValueError(f"unsafe repository path: {path!r}")
    return "/".join(parts)
