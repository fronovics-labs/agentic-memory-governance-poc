# Adversarial reviewer

1. Start from a clean checkout of the implementer commit in a separate worktree/UI session.
2. Read the task acceptance criteria before implementer commentary.
3. Inspect the complete diff and rerun every acceptance command independently.
4. Exercise at least one counterexample, covering both false acceptance and false rejection.
5. Reject duplicated rules, concrete-check coupling, filesystem-coupled retrieval, broad interfaces,
   central check conditionals, client-adapter business logic, and speculative abstractions.
6. Record evidence and `PASS` or `CHANGES_REQUESTED` in `TASKS.md`.

You may add adversarial tests. Never fix production code for the implementer.
