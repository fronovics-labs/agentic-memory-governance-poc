# Repository instructions

Read `ARCHITECTURE.md` and the selected `TASKS.md` item before changing code.

## Workflow

- Work on exactly one P01-P09 item in an isolated worktree.
- Implement only its acceptance criteria; do not seed experiment tasks, violations, metrics, or results.
- Run every acceptance command and record the exact command and result in `TASKS.md`.
- The implementer commits and sets `READY_FOR_REVIEW`; the implementer never records `PASS`.
- The reviewer starts from a clean checkout, reads criteria before commentary, inspects the full diff,
  reruns commands, and exercises at least one false-acceptance and false-rejection counterexample.
- Reviewers may add adversarial tests and update review evidence, but never fix production code.

## Design constraints

- Preserve the dependency rules in `ARCHITECTURE.md`.
- Prefer the standard library and existing code. Do not add speculative abstractions.
- Keep hook business behavior in `src/lab/hooks/core.py`; adapters translate JSON only.
- Keep concrete governance checks out of the engine.
- Keep mutable run artifacts outside the baseline repository and its run worktrees.

## Required checks

```bash
uv run ruff check .
uv run mypy
uv run pytest
```
