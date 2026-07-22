from lab.governance.engine import GovernanceEngine
from lab.governance.model import CheckContext, Violation


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
