from typing import cast

import pytest

from lab.governance.engine import GovernanceEngine
from lab.governance.model import CheckContext, GovernanceCheck, Violation


class FailingCheck:
    @property
    def id(self) -> str:
        return "test.failing"

    def evaluate(self, context: CheckContext) -> list[Violation]:
        return [Violation(self.id, f"failure during {context.phase}")]


class CrashingCheck:
    @property
    def id(self) -> str:
        return "test.crashing"

    def evaluate(self, context: CheckContext) -> list[Violation]:
        raise RuntimeError("boom")


def test_audit_records_all_violations_and_allows_completion() -> None:
    result = GovernanceEngine([CrashingCheck(), FailingCheck()]).evaluate(
        CheckContext(phase="completion"), "audit"
    )

    assert result.allowed is True
    assert [violation.check_id for violation in result.violations] == [
        "test.crashing",
        "test.failing",
    ]
    assert result.violations[0].message == "check crashed: RuntimeError: boom"


def test_block_returns_all_violations_and_rejects_completion() -> None:
    result = GovernanceEngine([FailingCheck(), CrashingCheck()]).evaluate(
        CheckContext(phase="completion"), "block"
    )

    assert result.allowed is False
    assert [violation.check_id for violation in result.violations] == [
        "test.failing",
        "test.crashing",
    ]


def test_engine_allows_clean_block_mode_and_registers_new_check_without_changes() -> None:
    class CleanCheck:
        @property
        def id(self) -> str:
            return "test.clean"

        def evaluate(self, context: CheckContext) -> list[Violation]:
            return []

    result = GovernanceEngine([CleanCheck()]).evaluate(CheckContext(phase="completion"), "block")

    assert result.allowed is True
    assert result.violations == ()


@pytest.mark.parametrize("check_id", ["", " ", "bad id", "../bad"])
def test_engine_rejects_unsafe_check_ids(check_id: str) -> None:
    class InvalidIdCheck:
        @property
        def id(self) -> str:
            return check_id

        def evaluate(self, context: CheckContext) -> list[Violation]:
            return []

    with pytest.raises(ValueError, match="nonblank safe identifier"):
        GovernanceEngine([InvalidIdCheck()])


def test_engine_rejects_duplicate_check_ids() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        GovernanceEngine([FailingCheck(), FailingCheck()])


def test_invalid_output_becomes_violation_without_suppressing_later_check() -> None:
    class InvalidOutputCheck:
        @property
        def id(self) -> str:
            return "test.invalid_output"

        def evaluate(self, context: CheckContext) -> object:
            return ["not a violation"]

    invalid = cast(GovernanceCheck, InvalidOutputCheck())
    result = GovernanceEngine([invalid, FailingCheck()]).evaluate(
        CheckContext(phase="completion"), "block"
    )

    assert [violation.check_id for violation in result.violations] == [
        "test.invalid_output",
        "test.failing",
    ]
    assert "check output must contain only Violation values" in result.violations[0].message


def test_engine_normalizes_spoofed_violation_identity() -> None:
    class SpoofingCheck:
        @property
        def id(self) -> str:
            return "test.spoofing"

        def evaluate(self, context: CheckContext) -> list[Violation]:
            return [Violation("test.failing", "spoofed")]

    result = GovernanceEngine([SpoofingCheck()]).evaluate(CheckContext(phase="completion"), "block")

    assert result.violations == (Violation("test.spoofing", "spoofed"),)
