"""Protocol-driven governance evaluation engine."""

from collections.abc import Iterable

from lab.governance.model import (
    CheckContext,
    GovernanceCheck,
    GovernanceMode,
    GovernanceResult,
    Violation,
)


class GovernanceEngine:
    def __init__(self, checks: Iterable[GovernanceCheck]) -> None:
        self._checks = tuple(checks)
        ids = [check.id for check in self._checks]
        if len(ids) != len(set(ids)):
            raise ValueError("governance check IDs must be unique")

    def evaluate(self, context: CheckContext, mode: GovernanceMode) -> GovernanceResult:
        if mode not in ("audit", "block"):
            raise ValueError(f"unsupported governance mode: {mode}")

        violations: list[Violation] = []
        for check in self._checks:
            try:
                violations.extend(check.evaluate(context))
            except Exception as error:
                violations.append(
                    Violation(
                        check_id=check.id,
                        message=f"check crashed: {type(error).__name__}: {error}",
                    )
                )
        return GovernanceResult(
            mode=mode,
            violations=tuple(violations),
            allowed=mode == "audit" or not violations,
        )
