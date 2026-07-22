"""Governance check and evaluation contracts."""

from dataclasses import dataclass
from typing import Literal, Protocol

GovernanceMode = Literal["audit", "block"]
GovernancePhase = Literal["pre_write", "completion"]


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    exit_code: int

    def __post_init__(self) -> None:
        if not self.command:
            raise ValueError("command must not be empty")


@dataclass(frozen=True, slots=True)
class CheckContext:
    phase: GovernancePhase
    changed_paths: tuple[str, ...] = ()
    baseline_manifest_path: str | None = None
    baseline_manifest_valid: bool = True
    commands: tuple[CommandResult, ...] = ()

    def __post_init__(self) -> None:
        if self.phase not in ("pre_write", "completion"):
            raise ValueError(f"unsupported governance phase: {self.phase}")


@dataclass(frozen=True, slots=True)
class Violation:
    check_id: str
    message: str
    path: str | None = None


class GovernanceCheck(Protocol):
    @property
    def id(self) -> str: ...

    def evaluate(self, context: CheckContext) -> list[Violation]: ...


@dataclass(frozen=True, slots=True)
class GovernanceResult:
    mode: GovernanceMode
    violations: tuple[Violation, ...]
    allowed: bool
