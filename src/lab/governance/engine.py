"""Protocol-driven governance evaluation engine."""

from collections.abc import Iterable

from lab.governance.model import (
    CheckContext,
    GovernanceCheck,
    GovernanceMode,
    GovernanceResult,
    Violation,
    validate_check_id,
)


class GovernanceEngine:
    def __init__(self, checks: Iterable[GovernanceCheck]) -> None:
        registered = tuple((validate_check_id(check.id), check) for check in checks)
        ids = [check_id for check_id, _ in registered]
        if len(ids) != len(set(ids)):
            raise ValueError("governance check IDs must be unique")
        self._checks = registered

    def evaluate(self, context: CheckContext, mode: GovernanceMode) -> GovernanceResult:
        if mode not in ("audit", "block"):
            raise ValueError(f"unsupported governance mode: {mode}")

        violations: list[Violation] = []
        for check_id, check in self._checks:
            try:
                returned = check.evaluate(context)
                if not isinstance(returned, list):
                    raise TypeError("check output must be list[Violation]")
                if any(not isinstance(violation, Violation) for violation in returned):
                    raise TypeError("check output must contain only Violation values")
                violations.extend(
                    Violation(check_id, violation.message, violation.path) for violation in returned
                )
            except Exception as error:
                violations.append(
                    Violation(
                        check_id=check_id,
                        message=f"check crashed: {type(error).__name__}: {error}",
                    )
                )
        return GovernanceResult(
            mode=mode,
            violations=tuple(violations),
            allowed=mode == "audit" or not violations,
        )
