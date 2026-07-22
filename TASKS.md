# Part 1 build tracker

No experiment tasks, seeded violations, measurements, results, or conclusions belong in P01-P09.
An implementer sets `READY_FOR_REVIEW`; only an independent reviewer sets `PASS`.

## P01 — Scaffold, architecture contract and tracker

Status: READY_FOR_REVIEW
Implementer commit: HEAD (resolved to the commit supplied for review)
Review round: 2

### Acceptance criteria

- The documented repository tree exists, with importable Python package boundaries and all four test areas.
- `ARCHITECTURE.md` assigns one responsibility and owner to every top-level production surface.
- Dependency direction, shared-hook ownership, governance extensibility, protected paths, and external run-artifact boundaries are explicit and unambiguous.
- Python 3.12, pytest, Ruff, mypy, the `lab` entrypoint, and a dependency lock are configured.
- `AGENTS.md`, `CLAUDE.md`, and both agent role documents enforce the independent two-worktree review workflow.
- P02-P09 behavior and all experiment-specific tasks, violations, measurements, and results are absent.

### Implementer evidence

- Files changed: `ARCHITECTURE.md`, `TASKS.md`, `AGENTS.md`, `CLAUDE.md`, both
  `agents/` role contracts, `pyproject.toml`, `uv.lock`, `.python-version`, hook config
  placeholders, `scripts/lab`, the documented `sample_app/` and `src/lab/` package tree, and all
  four `tests/` areas.
- Commands executed:
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv lock`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv sync --dev`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run python --version`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff format --check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run mypy`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest -q`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache scripts/lab --help`
  - `python3 -m json.tool .claude/settings.json`
  - `python3 -m json.tool .codex/hooks.json`
  - `git diff --check`
- Results: lock resolved 14 packages; sync installed 13 packages; Python `3.12.13`; Ruff format
  `26 files already formatted`; Ruff lint `All checks passed!`; mypy
  `Success: no issues found in 26 source files`; pytest `1 passed in 0.02s`; `lab --help` exited 0
  with the expected `usage: lab [-h]`; both hook JSON files parsed; diff check exited 0.
- Re-review fix: assigned the platform CLI surface (`scripts/lab`, `src/lab/cli.py`, and
  `src/lab/__main__.py`) an explicit responsibility and `Platform integration` owner in
  `ARCHITECTURE.md`.
- Re-review commands: `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff format
  --check .`; `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff check .`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run mypy`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest -q`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache scripts/lab --help`; `git diff --check`.
- Re-review results: Ruff format `26 files already formatted`; Ruff lint `All checks passed!`;
  mypy `Success: no issues found in 26 source files`; pytest `1 passed in 0.02s`; `lab --help`
  exited 0 with `usage: lab [-h]`; diff check exited 0.

### Adversarial review

- Clean checkout: detached reviewer worktree at
  `15326a87abf44c81a462e93971649cd20d8d9700`; clean before review.
- Diff inspected: complete 43-file diff against `5893370babc84928a6a9615e3656118b6b47acc7`.
- Counterexamples: an independent AST boundary gate rejected a synthetic
  `domain -> infrastructure` import and accepted the valid
  `infrastructure -> application/domain` direction; all current scaffold imports passed. Package
  imports also succeeded from `/private/tmp`, outside the repository working directory.
- SOLID findings: `ARCHITECTURE.md` does not assign a responsibility or owner to the platform CLI
  surface (`scripts/lab`, `src/lab/cli.py`, and `src/lab/__main__.py`). The sample-app CLI has an
  explicit row, so ownership of the platform entrypoint is ambiguous and the second acceptance
  criterion is not met. No production abstraction, concrete-check coupling, or forbidden
  dependency exists yet.
- DRY findings: no duplicated business or hook logic; P02-P09 modules are inert placeholders.
- Commands executed: `uv sync --frozen --dev`; `uv run python --version` (`3.12.13`);
  `uv run ruff format --check .` (`26 files already formatted`); `uv run ruff check .` (passed);
  `uv run mypy` (26 files, passed); `uv run pytest -q` (1 passed); `scripts/lab --help` (passed);
  independent JSON/TOML/diff, required-path, package-import, external-CWD import, scope, and AST
  boundary checks (passed).
- Round 2 clean checkout: detached reviewer worktree at
  `7d102295e0218043a426da85dcd770c435f4938d`; clean before review.
- Round 2 diff inspected: complete delta from rejected commit `15326a87` contains only the prior
  review record, its implementer follow-up evidence, and the one-line `ARCHITECTURE.md` ownership
  fix; no production behavior or experiment scope was added.
- Round 2 counterexamples: the ownership gate covers every production surface, rejects an omitted
  platform CLI owner, and accepts one combined row for the three parts of the same entrypoint. The
  AST dependency gate still rejects `domain -> infrastructure` and accepts
  `infrastructure -> application/domain`.
- Round 2 SOLID/DRY findings: the platform CLI now has one explicit `Platform integration` owner
  and delegates behavior to owning modules. The prior ambiguity is resolved with no new
  abstraction or duplicated rule.
- Round 2 commands executed: `uv run ruff format --check .` (26 files); `uv run ruff check .`;
  `uv run mypy` (26 files); `uv run pytest -q` (1 passed); `scripts/lab --help`; `git diff
  --check`; independent ownership and AST counterexample gates. All passed.

### Verdict

PASS

## P02 — Synthetic order service

Status: READY_FOR_REVIEW
Implementer commit: HEAD (resolved to the commit supplied for review)

### Acceptance criteria

- A user can create, retrieve, and list orders through the sample CLI with SQLite persistence.
- Domain rules have no application, infrastructure, CLI, or lab dependency.
- Application use cases depend on a repository port; only the composition root selects SQLite.
- Business rules are not duplicated across domain, application, infrastructure, or CLI code.
- Unit, contract, and integration tests cover success, missing-order, invalid-input, and persistence behavior.

### Implementer evidence

- Files changed: `sample_app/domain/order.py`, `sample_app/application/orders.py`,
  `sample_app/infrastructure/sqlite_orders.py`, `sample_app/cli.py`,
  `tests/unit/test_order.py`, `tests/contract/test_order_service.py`,
  `tests/integration/test_order_cli.py`, and this tracker.
- Commands executed:
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff format --check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run mypy`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest -q`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run python -m sample_app.cli --database /private/tmp/p02-cli-evidence.YMOo3Y/orders.sqlite3 create --id order-001 --item widget --quantity 2`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run python -m sample_app.cli --database /private/tmp/p02-cli-evidence.YMOo3Y/orders.sqlite3 get --id order-001`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run python -m sample_app.cli --database /private/tmp/p02-cli-evidence.YMOo3Y/orders.sqlite3 list`
  - The same CLI with `get --id missing` and `create --id bad --item widget --quantity 0`.
- Results: Ruff format `32 files already formatted`; Ruff lint `All checks passed!`; mypy
  `Success: no issues found in 32 source files`; pytest `9 passed in 1.28s`; create and a separate
  get process both returned `{"item": "widget", "order_id": "order-001", "quantity": 2}`;
  list returned the persisted order; missing and invalid commands exited 1 with `order not found:
  missing` and `quantity must be a positive integer` respectively.

### Adversarial review

- Clean checkout: detached reviewer worktree at
  `14c30d9478508bfc9e801ed5d464f136e85cd82a`; clean before review.
- Diff inspected: complete eight-file P02 diff against parent `066cccb`, plus every caller of
  `Order`, `OrderService`, `OrderRepository`, and `SQLiteOrderRepository`.
- Counterexamples: separate OS processes created orders in reverse lexical order, retrieved them,
  and listed them twice after reopening SQLite; output remained ordered by ID and persisted rows
  matched the database. Missing, duplicate, zero, non-integer, blank, and missing-argument inputs
  returned nonzero with no success output or added row. A quoted SQL-like ID round-tripped as data.
  An invalid database location returned nonzero with no success output. Direct domain/service calls
  rejected empty, whitespace-only, non-string, boolean, zero, and negative values, while nonblank
  whitespace-containing text remained valid as the documented rule permits.
- SOLID findings: domain imports only the standard library; application depends on the domain and
  the minimal three-method repository port; infrastructure depends inward on that port/domain; only
  the CLI selects SQLite. The infrastructure traceback for an invalid database location is not a
  P02 blocker because the task requires failure, not a friendly operational-error contract.
- DRY findings: order validation exists only in `Order`; the CLI and service reuse it. SQLite owns
  persistence constraints and maps its primary-key failure to the application error once. No
  duplicated production business rule or speculative abstraction found.
- Commands executed: `uv run ruff format --check .` (32 files); `uv run ruff check .`; `uv run
  mypy` (32 files); `uv run pytest -q` (9 passed); `git diff --check`; independent fresh-process
  CLI/SQLite/order/injection/failure checks; direct domain/service validation and AST import-boundary
  checks. All acceptance gates passed.

### Verdict

PASS

## P03 — Memory model and Markdown repository

Status: READY_FOR_REVIEW
Implementer commit: HEAD (resolved to the commit supplied for review)
Review round: 2

### Acceptance criteria

- Markdown with TOML front matter round-trips all required fields: `id`, `type`, `authority`, `status`, `scopes`, `owner`, `source_ids`, `enforcement_ids`, `valid_from`, `valid_until`, and `supersedes`.
- `lab memory validate` deterministically reports malformed metadata, duplicate IDs, invalid references, and supersession cycles with nonzero exit status.
- Validation does not reject valid open-ended dates or empty reference lists.
- Parsing and storage are separate from retrieval, rendering, and governance.
- Repository tests cover safe path handling and stable ordering without adding embeddings or a vector database.

### Implementer evidence

- Files changed: `src/lab/memory/model.py`, `src/lab/memory/repository.py`, `src/lab/cli.py`,
  `tests/unit/test_memory.py`, `tests/contract/test_memory_repository.py`,
  `tests/integration/test_memory_cli.py`, and this tracker.
- Commands executed:
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff format --check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run mypy`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest -q`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run lab memory validate --directory /private/tmp/p03-memory-evidence.X97S4J` with one valid memory.
  - The same validation command after adding `ADR-002` with `supersedes = "MISSING"`.
- Results: Ruff format `35 files already formatted`; Ruff lint `All checks passed!`; mypy
  `Success: no issues found in 35 source files`; pytest `18 passed in 1.43s`; the valid corpus
  exited 0 with `valid: 1 memories`; the invalid-reference corpus exited 1 with `ADR-002:
  supersedes unknown memory MISSING`.
- Re-review fix: missing configured roots now fail validation, and repository save/load rejects a
  symlink in any configured-root ancestor before directory creation or file access.
- Re-review regressions: contract tests cover missing-root validation, save through an ancestor
  symlink with an assertion that no outside directory/file was created, and load through an ancestor
  symlink; an integration test covers the missing-root CLI exit and diagnostic.
- Re-review commands: `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff format --check
  .`; `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff check .`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run mypy`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest -q`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run lab memory validate --directory
  /private/tmp/p03-round2-evidence.dLrBac/missing`; `git diff --check`.
- Re-review results: Ruff format `35 files already formatted`; Ruff lint `All checks passed!`;
  mypy `Success: no issues found in 35 source files`; pytest `22 passed in 1.53s`; missing-root CLI
  validation exited 1 with `memory directory does not exist:
  /private/tmp/p03-round2-evidence.dLrBac/missing`; diff check exited 0.

### Adversarial review

- Clean checkout: detached reviewer worktree at
  `2e2c3542e05c6e4edb76238931f4276c27ad8743`; clean before review.
- Diff inspected: complete seven-file P03 diff against parent `e56b068`, plus all model,
  repository, validation CLI, and test callers.
- Counterexamples: all required-field omissions and wrong types were rejected; Unicode, escaping,
  a body `+++` line, empty references/open dates, bounded dates, self/2/3-node cycles, dangling
  supersedes, duplicate IDs, and acyclic chain/diamond controls behaved deterministically. Recursive
  path ordering, invalid UTF-8, final-root/file symlinks, repeated CLI diagnostics, and traversal-like
  identifiers were also exercised.
- SOLID findings: parsing/model invariants and filesystem storage remain separate from the still-inert
  retrieval, context-rendering, governance, and hook modules. No P04+ behavior, embedding, vector
  dependency, broad interface, or speculative abstraction was added.
- DRY findings: required fields, date/reference rules, TOML parsing/rendering, and collection graph
  validation each have one production implementation.
- Defects: `MarkdownMemoryRepository._paths()` returns an empty list when the configured root does
  not exist, so `lab memory validate --directory <typo>` exits 0 with `valid: 0 memories`. A missing
  repository root must fail honestly rather than falsely validate an unintended empty corpus.
  `save()` checks only whether the final root component is a symlink; with
  `<base>/link/nested-items` where `link` targets an outside directory, it creates
  `nested-items/ADR.md` outside `<base>` and accepts it because both comparisons use the resolved
  outside root. Symlinked ancestors must be rejected before directory creation or file access.
- Commands executed: `uv run ruff format --check .` (35 files); `uv run ruff check .`; `uv run
  mypy` (35 files); `uv run pytest -q` (18 passed); `git diff --check`; direct field/type/date/
  round-trip/reference/cycle/DAG checks; recursive ordering, missing-root, traversal/symlink, UTF-8,
  and repeated subprocess CLI checks. Standard gates passed; the two boundary counterexamples did not.
- Round 2 clean checkout: detached reviewer worktree at
  `aa4d7ba6c8fbdc643624495afc9cd0ebfa8991b0`; clean before review.
- Round 2 diff inspected: focused four-file delta from rejected commit `2e2c354` contains the root
  safety fix, its contract/integration regressions, and tracker evidence only; no P04+ scope.
- Round 2 counterexamples: a nonexistent root now fails repository and subprocess CLI validation
  with no directory creation. Save and load through an ancestor symlink both fail before access, and
  no outside directory or memory file is created. As a false-rejection control, an ordinary missing
  nested root is still created by `save()`, then loads and validates normally.
- Round 2 SOLID/DRY findings: one root-check helper covers save/load/validate without duplicating
  policy or coupling storage to retrieval/rendering/governance. No new abstraction was added.
- Round 2 commands executed: Ruff format/lint (35 files), mypy (35 files), full pytest (22 passed),
  focused repository/CLI pytest (9 passed), diff check, and direct missing-root, ancestor-symlink,
  no-outside-artifact, and safe-root controls. All passed.

### Verdict

PASS

## P04 — Retrieval and context rendering

Status: READY_FOR_REVIEW
Implementer commit: HEAD (resolved to the commit supplied for review)
Review round: 2

### Acceptance criteria

- `lab memory search --query TEXT` performs deterministic keyword retrieval.
- `lab memory context --prompt TEXT` applies prompt keywords and applicable path scope, then renders concise context with memory IDs and authority levels.
- Expired, not-yet-valid, inactive, superseded, and wrong-scope memories never leak into results.
- Retrieval depends on a repository port rather than Markdown or filesystem implementation details.
- Ranking and rendering are stable, and false-acceptance/false-rejection tests cover nearby keywords and glob boundaries.

### Implementer evidence

- Files changed: `src/lab/memory/retrieval.py`, `src/lab/memory/renderer.py`, `src/lab/cli.py`,
  `tests/unit/test_retrieval.py`, `tests/integration/test_memory_retrieval_cli.py`, and this tracker.
- Commands executed:
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff format --check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run mypy`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest -q`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run lab memory search --query 'order persistence' --directory /private/tmp/p04-memory-evidence.s1cLig`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run lab memory context --prompt 'change order persistence' --path sample_app/application/orders.py --directory /private/tmp/p04-memory-evidence.s1cLig`
  - The same context command with path `sample_app/infrastructure/sqlite_orders.py`.
- Results: Ruff format `37 files already formatted`; Ruff lint `All checks passed!`; mypy
  `Success: no issues found in 37 source files`; pytest `29 passed in 2.28s`; search returned active
  `ADR-001` then `ADR-003` with IDs and authority, excluding inactive `ADR-002`; application
  context returned only scoped `ADR-001`; the wrong-path context returned no output; all direct
  commands exited 0.
- Re-review fix: `context --path` is required, and retrieval rejects absolute, dot-segment,
  traversal, empty/repeated-separator, trailing-separator, backslash, and Windows-drive target paths
  before loading or scope matching.
- Re-review regressions: parameterized unit counterexamples cover each rejected form; integration
  checks cover missing and traversal CLI paths; normalized relative application paths remain an
  explicit false-rejection control.
- Re-review commands: `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff format --check
  .`; `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff check .`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run mypy`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest -q`; three direct `lab memory
  context` commands with missing, traversal, and valid paths; `git diff --check`.
- Re-review results: Ruff format `37 files already formatted`; Ruff lint `All checks passed!`;
  mypy `Success: no issues found in 37 source files`; pytest `39 passed in 8.15s`; missing path
  exited 2 with `the following arguments are required: --path`; traversal exited 1 with
  `target path must be a normalized relative POSIX path`; valid application path exited 0 and
  rendered only `[ADR-001 | mandatory]` context.

### Adversarial review

- Clean checkout: detached reviewer worktree at
  `fd656e9221537398fe8c11874833437804ea7d43`; clean before review.
- Diff inspected: complete six-file P04 diff against parent `e15045c`, plus every retrieval,
  renderer, repository-port, and CLI caller.
- Counterexamples: shuffled fake-repository order, duplicate/case/Unicode/punctuation tokens,
  nearby words, stable ties, inclusive/open/future/expired dates, inactive records, successor chains,
  inactive/future/expired/wrong-scope successors, empty/global/multiple scopes, exact/`*`/`**` glob
  boundaries, sibling prefixes, cycles from an invalid fake port, and instruction-like rendered bodies
  were exercised. Ranking/rendering remained byte-stable and normal controls passed.
- SOLID findings: retrieval depends only on a one-method `MemoryRepository` protocol and the model;
  it has no filesystem/Markdown adapter dependency. Rendering is separate, and the CLI alone composes
  the concrete repository. No P05+, embedding, vector, strategy, or speculative abstraction exists.
- DRY findings: lifecycle/supersession filtering, tokenization/scoring, glob matching, tie-breaking,
  and context rendering each have one production implementation shared by search/context.
- Defects: `context --path` is optional; when omitted, `_applies_to_path(..., None)` accepts every
  scoped memory, so a context command returns application-only memory without any target path.
  Context must require an explicit path to enforce its promised scope filter. Also,
  `PurePosixPath` preserves `..` components and `_path_matches` lets `**` consume them: target
  `sample_app/application/../domain/order.py` matches scope `sample_app/application/**` and leaks
  application memory into a logically domain path. Reject non-normalized/unsafe target paths (or
  normalize without allowing root escape) before matching.
- Commands executed: `uv run ruff format --check .` (37 files); `uv run ruff check .`; `uv run
  mypy` (37 files); `uv run pytest -q` (29 passed); `git diff --check`; direct shuffled lifecycle,
  supersession, token/rank, glob/path, render-boundary, repository-port AST, and subprocess CLI
  success/error/stability checks. Standard gates passed; both wrong-scope counterexamples failed.
- Round 2 clean checkout: detached reviewer worktree at
  `fe3c763c4fb117f6c973a8097123ca4ed6dc4596`; clean before review.
- Round 2 diff inspected: focused five-file delta from rejected commit `fd656e9` contains only the
  target-path guard, required CLI argument, regressions, and tracker evidence; no scope creep.
- Round 2 counterexamples: missing `--path` fails at argparse; empty, absolute, dot, traversal,
  repeated/trailing separator, backslash, and Windows-drive forms fail before repository loading.
  The original traversal returns no context. A normalized relative application path renders the
  scoped memory, while a valid domain path remains an empty successful result.
- Round 2 SOLID/DRY findings: one path validator protects direct and CLI retrieval before glob
  matching without filesystem coupling or duplicated scope policy. No new abstraction was added.
- Round 2 commands executed: Ruff format/lint (37 files), mypy (37 files), full pytest (39 passed),
  focused retrieval/CLI pytest (17 passed), diff check, direct pre-load path rejection, and subprocess
  missing/traversal/valid/wrong-scope controls. All passed.

### Verdict

PASS

## P05 — Governance engine

Status: READY_FOR_REVIEW
Implementer commit: HEAD (resolved to the commit supplied for review)
Review round: 2

### Acceptance criteria

- Checks implement the documented protocol and register without editing the engine.
- `audit` records every violation and allows completion; `block` returns every violation and rejects completion.
- One failing or crashing check cannot suppress another check's result.
- Platform checks protect `.org-memory/`, hook configuration, governance checks, and baseline manifests, and run formatting, types, and tests before completion.
- No concrete check import, central type conditional, experiment-specific architectural check, or duplicated business rule exists in the engine.

### Implementer evidence

- Files changed: `src/lab/governance/model.py`, `src/lab/governance/engine.py`,
  `src/lab/governance/checks/__init__.py`, `src/lab/governance/checks/platform.py`,
  `tests/unit/test_governance_checks.py`, `tests/contract/test_governance_engine.py`, and this
  tracker.
- Commands executed:
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff format --check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff check .`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run mypy`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest -q`
  - `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest tests/unit/test_governance_checks.py tests/contract/test_governance_engine.py -q`
  - A direct Python invocation registering all three platform checks and evaluating a failing
    completion context in both `audit` and `block` modes.
- Results: Ruff format `40 files already formatted`; Ruff lint `All checks passed!`; mypy
  `Success: no issues found in 40 source files`; pytest `46 passed in 1.91s`; focused governance
  tests `7 passed in 0.04s`; direct evaluation returned `audit` allowed with all 5 violations and
  `block` rejected with the same 5 violations.
- Re-review fix: completion governance now executes four fixed argv tuples through shell-free
  `subprocess.run` with configured cwd/timeout, captured bounded output, and all-command failure
  aggregation. Repository paths are canonicalized before checks and protected surfaces match only
  at the repository root. The engine validates safe unique IDs, list/`Violation` outputs, and
  normalizes every returned violation to its registered check ID.
- Re-review regressions: tests cover nonzero, timeout, `OSError`, runner exceptions/mismatch,
  bounded output, all-run behavior, exact argv/cwd/timeout, unsafe paths, safe vendor/copy
  lookalikes, blank/unsafe/duplicate check IDs, malformed outputs, later-check survival, and spoofed
  IDs.
- Re-review commands: `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff format --check
  .`; `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run ruff check .`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run mypy`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest -q`;
  `UV_CACHE_DIR=/private/tmp/agentic-memory-uv-cache uv run pytest
  tests/unit/test_governance_checks.py tests/contract/test_governance_engine.py -q`; direct production
  `CompletionCommandsCheck` evaluation in the implementation worktree; `git diff --check`.
- Re-review results: Ruff format `40 files already formatted`; Ruff lint `All checks passed!`;
  mypy `Success: no issues found in 40 source files`; pytest `61 passed in 1.83s`; focused governance
  tests `22 passed in 0.07s`; the production default runner executed Ruff format/lint, mypy, and
  pytest and returned `violations=0`.

### Adversarial review

- Clean checkout: detached reviewer worktree at
  `7ff1a21edc332db29bcb1b11f1333f25418948e5`; clean before review.
- Diff inspected: complete seven-file P05 diff against parent `38be6fe`, every governance model,
  engine/check caller, and the still-inert P06 hook/adapters.
- Counterexamples: audit/block returned identical ordered violations with only `allowed` differing;
  a two-violation check, crashing check, and later check all survived in order. Unknown mode and
  duplicate IDs rejected. Exact protected paths, normalized aliases, rename source/destination,
  sibling-prefix controls, selected-manifest alias/sibling, and manifest mismatch behaved as intended.
- SOLID findings: the engine imports only protocols/models and contains one generic aggregation loop;
  concrete platform checks are injected. No concrete-check conditional, P06 behavior, hook logic, or
  experiment-specific check exists.
- DRY findings: path matching, manifest comparison, completion-name recognition, and engine
  aggregation are each centralized; no audit/block duplication.
- Defects: completion commands are never run. `CompletionCommandsCheck` only trusts caller-created
  `CommandResult(command, exit_code)` values; there is no production caller/runner, subprocess use,
  timeout/OSError/output representation, bounded output, or all-run behavior. Four fabricated zero
  exit codes pass all completion gates without executing Ruff, mypy, or pytest, so the P05 completion
  requirement is false-accepting.
  Path canonicalization also accepts empty, absolute, Windows-drive, and root-escaping targets such
  as `../../etc/passwd` with no violation. Conversely, because protected segments may occur anywhere,
  safe repo-relative lookalikes such as `vendor/.org-memory/A.md`,
  `vendor/.claude/settings.json`, and `copy/src/lab/governance/checks/x.py` are falsely blocked.
  Paths must be validated as normalized repo-relative identities and matched only at the repository
  root. Finally, the engine accepts a blank check ID, extends a returned `list[str]` into the result,
  and accepts a check returning a `Violation` with another check's ID. Invalid IDs/outputs must fail
  honestly instead of corrupting or spoofing governance results.
- Commands executed: Ruff format/lint (40 files), mypy (40 files), full pytest (46 passed), focused
  governance pytest (7 passed), diff check, direct aggregation/crash/parity/malformed-output checks,
  table-driven protected/unsafe/lookalike/rename/manifest paths, and forged completion results.
  Standard gates passed; the three fail-open counterexample groups did not.
- Round 2 clean checkout: detached reviewer worktree at
  `c8e9cf4229ff4fc88bd378b358d49fd401d48293`; clean before review.
- Round 2 diff inspected: focused six-file delta from rejected commit `7ff1a21` contains the three
  boundary fixes, regressions, and tracker evidence only; no P06 or experiment scope.
- Round 2 counterexamples: the production default runner executed all four fixed shell-free commands
  with zero violations. Injected nonzero, timeout, `OSError`, huge output, and mismatched-result cases
  still ran every command and produced four bounded violations. Unsafe/escaping paths and an empty
  manifest identity reject at context creation; exact root surfaces block while vendor/copy
  lookalikes remain allowed. Blank/unsafe IDs reject, malformed output becomes a crash violation
  without suppressing the next check, and spoofed violation identity is normalized.
- Round 2 SOLID/DRY findings: engine remains protocol-only and generic; one root path validator, one
  anchored matcher, and one command runner/error mapper cover the fixes without central check types
  or duplicated audit/block logic.
- Round 2 commands executed: Ruff format/lint (40 files), mypy (40 files), full pytest (61 passed),
  focused governance pytest (22 passed), diff check, direct path/manifest/engine/all-run failure
  matrix, and real default completion execution. All passed.

### Verdict

PASS

## P06 — Claude and Codex adapters

Status: READY_FOR_REVIEW
Implementer commit: HEAD (resolved to the commit supplied for review)

### Acceptance criteria

- One shared core implements `UserPromptSubmit`, `PreToolUse`, and `Stop` behavior for both clients.
- Prompt submission injects the same applicable memory IDs, authority levels, and content through each client's JSON shape.
- Pre-tool handling blocks protected writes and destructive reset/baseline commands while allowing adjacent safe operations.
- Stop handling logs and allows in `audit`, and reports and continues work in `block`.
- Adapters contain only input/output translation; parity, malformed-input, false-acceptance, and false-rejection contract tests cover both clients.

### Implementer evidence

- Files changed: `src/lab/hooks/core.py`, `src/lab/hooks/_adapter.py`,
  `src/lab/hooks/claude_adapter.py`, `src/lab/hooks/codex_adapter.py`, `scripts/lab-hook`,
  `.claude/settings.json`, `.codex/hooks.json`, `tests/contract/test_hook_adapters.py`, and this
  tracker.
- Commands executed: Ruff format/check, mypy, full pytest, focused hook contracts, JSON parsing for
  both committed config files, and direct JSON stdin invocations of both executable adapters.
- Results: Ruff format `42 files already formatted`; Ruff lint `All checks passed!`; mypy `Success:
  no issues found in 42 source files`; full pytest `114 passed in 1.81s`; focused hook contracts `53
  passed in 0.27s`; both config files parsed; direct Claude protected-write and Codex destructive
  baseline requests returned structured `PreToolUse` denials.
- Contract coverage: both clients receive byte-equivalent rendered memory provenance; exact protected
  paths, patch targets, redirects, and indirect script writes deny; reset/freeze commands including
  wrappers deny; adjacent reads, verification, quoted text, and lookalike paths allow; audit Stop logs
  violations while allowing, block Stop returns continuation reasons; malformed JSON-domain inputs
  fail identically at both adapter boundaries.
- Re-review fixes: safe tool calls now return no permission decision; event cwd is carried separately
  from the discovered repository root; newline, subshell, command-substitution, and shell `-c` reset
  forms deny without treating quoted text as execution; an active Stop continuation records failures
  but does not block again; malformed `PreToolUse` returns the supported nested deny shape.
- Re-review results: Ruff format `42 files already formatted`; Ruff lint `All checks passed!`; mypy
  `Success: no issues found in 42 source files`; full pytest `130 passed in 2.26s`; focused hook
  contracts `69 passed in 0.66s`. Direct subprocess checks confirmed a nested-cwd protected denial,
  a malformed Claude denial, and a permission-neutral safe Codex response.

### Adversarial review

- Clean checkout: detached reviewer worktree at
  `38bf7278e8662d346faba5504b8d2915d15d70d5`; clean before review.
- Diff inspected: complete nine-file P06 diff against the accepted P05 review commit, including both
  client configurations, executable boundary, shared adapter helpers/core, tests, and tracker. No P07
  run-worktree or baseline-lifecycle implementation leaked into the change.
- Counterexamples: both real adapter subprocesses allow `../.codex/hooks.json` from a nested `src/`
  event cwd and return exit zero plus an unsupported `continue: false` response for malformed
  `PreToolUse`. Both in-process clients allow destructive commands after a shell newline, in `$()`
  command substitution, and under `bash -lc`; both repeatedly block a `Stop` payload with
  `stop_hook_active: true`. An apply-patch move into `.codex/hooks.json` was denied, and the existing
  safe read/write lookalikes remained allowed.
- SOLID findings: lifecycle policy is centralized in `HookCore`; concrete adapters are thin and have
  no P07 responsibilities. However, `HookRequest` omits event cwd and Stop continuation state, so the
  shared core cannot implement the required client-neutral path and recursion policy correctly.
- DRY findings: Claude and Codex delegate to one translator, renderer, and core with no duplicated
  business-rule lists. The shared implementation means every defect below affects both clients
  identically rather than being an adapter-parity discrepancy.
- Defects: safe `PreToolUse` results emit `permissionDecision: "allow"`, which auto-approves ordinary
  Claude tool calls instead of reporting no governance objection and preserving the client's normal
  permission flow. Relative tool paths are resolved against repository root rather than event cwd,
  so protected writes from nested directories fail open. Shell parsing treats newlines and command
  substitutions as ordinary tokens and recognizes only exact `-c`, allowing valid destructive reset
  commands through. Stop input discards `stop_hook_active`, so an unchanged completion violation is
  re-blocked until the client's continuation cap. Finally, malformed `PreToolUse` input exits zero
  with top-level `continue: false`; Codex does not support that field for this event and continues the
  tool call, so the guard boundary fails open instead of denying or exiting 2.
- Commands executed: Ruff format check, Ruff lint, mypy, full pytest before adversarial tests, focused
  hook contracts after adversarial tests, diff check, and real Claude/Codex adapter subprocesses.
  Standard gates passed with `114 passed`; the expanded hook contracts produced `14 failed, 55
  passed`, covering all five defects above.
- Round 2 clean checkout: detached reviewer worktree at
  `4b9730bb9186d69299371a8b573d4222afcff771`; clean before re-review.
- Round 2 diff inspected: focused four-file delta from rejected commit `38bf727` contains the shared
  core/boundary fixes, regression expectation update, and tracker evidence only; adapters remain thin
  and no P07 scope was added.
- Round 2 counterexamples: both real adapter subprocesses deny the nested-cwd protected write and
  malformed `PreToolUse`; permission-neutral safe calls omit a decision; newline, `$()`, and
  `bash -lc` destructive resets deny for both clients; an active Stop continuation allows while
  preserving the completion violation in `systemMessage`. The accepted apply-patch move and safe
  lookalike controls remain green.
- Round 2 SOLID/DRY findings: event cwd and Stop continuation state now cross the shared request
  boundary once, and one renderer, one path normalizer, and one shell classifier serve both clients.
  No client-specific business rules or duplicate policy lists were introduced.
- Round 2 commands executed: focused hook contracts (`69 passed`), Ruff format check (`42 files`),
  Ruff lint, mypy (`42 source files`), full pytest (`130 passed`), and fix-delta diff check. All passed.

### Verdict

PASS

## P07 — Baseline, worktree and reset lifecycle

Status: READY_FOR_REVIEW
Implementer commit: HEAD (resolved to the commit supplied for review)

### Acceptance criteria

- `lab baseline freeze/verify --name NAME` records and verifies Git commit/tree, lock, memory, hook, governance-check, Python, and platform hashes.
- `lab run create --id ID --mode audit|block` creates a detached worktree from the frozen commit in the sibling runs directory.
- Reset deletes only the named run worktree, recreates it from the frozen commit, verifies every baseline hash, preserves external transcripts/logs/patches, and fails closed on mismatch.
- `lab run verify` and `lab run archive` are deterministic and reject unsafe IDs or paths.
- Dirty state, symlink/path escape, manifest tampering, failed reset, unrelated worktree preservation, and three consecutive identical resets are tested.

### Implementer evidence

- Files changed: `src/lab/runs/manifest.py`, `src/lab/runs/baseline.py`,
  `src/lab/runs/workspace.py`, `src/lab/cli.py`,
  `tests/integration/test_run_lifecycle.py`, and this tracker.
- Commands executed: Ruff format/check, mypy, full pytest, focused disposable-repository lifecycle
  tests, direct CLI lifecycle test with visible output, and `git diff --check`.
- Results: Ruff format `43 files already formatted`; Ruff lint `All checks passed!`; mypy `Success:
  no issues found in 43 source files`; full pytest `138 passed in 15.16s`; focused lifecycle `8
  passed in 11.02s`; direct CLI freeze/verify/create/verify/reset/archive `1 passed in 2.65s` with
  baseline, worktree, manifest, and patch paths in the external sibling runs directory.
- Coverage: manifests record commit/tree, dependency lock, controlled memory/hook/governance/platform
  hashes, Python, and host platform; freeze rejects dirty state; run creation is detached; verify
  detects protected-file changes; three resets reproduce identical commit/content while retaining
  logs, transcripts, and prior patches; unrelated worktrees survive; baseline and run-manifest
  tampering fail before deletion; archive captures the final patch externally; unsafe IDs, symlinked
  roots/artifact paths, and redirected worktree paths fail closed.
- Re-review fixes: controlled memory and governance inventories include untracked regular files;
  tracked and untracked worktree changes are combined into external binary patches; evidence is
  staged under a temporary name and finalized only after successful removal/replacement; reset and
  archive fully verify immutable commit hashes, manifest contents, run metadata, and the existing
  worktree before removal.
- Re-review results: Ruff format `43 files already formatted`; Ruff lint `All checks passed!`; mypy
  `Success: no issues found in 43 source files`; focused lifecycle regressions `13 passed in 35.90s`;
  full pytest `143 passed in 45.28s`; diff check passed.

### Adversarial review

- Clean checkout: detached reviewer worktree at
  `df80c3cc23a308faa141a1713d0c97e0a8d836f2`; clean before review.
- Diff inspected: complete six-file P07 delta from the accepted P06 review, including manifest
  schemas/hashing, baseline capture, run lifecycle, CLI composition, disposable-Git tests, and
  tracker. No P08 client launch, native-memory, or client-home behavior was added.
- Counterexamples: a real detached run containing an untracked governed memory still passes
  `run verify`. Reset and archive each emit an empty patch for an untracked application file and then
  delete its only copy. Locking the real worktree makes reset fail after `reset-0001.patch` is written;
  after unlock, retry is rejected because that patch filename already exists. Coordinated valid-schema
  baseline/run-manifest tampering is detected only after reset removes and recreates the worktree,
  replacing a modified file before reporting the mismatch. Existing clean create/verify, detached
  HEAD, tracked changes, unrelated worktree, artifact symlink, and three-reset controls pass.
- SOLID findings: baseline/manifest/workspace responsibilities are separated and the CLI delegates to
  them; Git uses fixed argv without shell interpolation. However, reset/archive lack a transaction or
  recoverable operation ordering around evidence capture, removal, recreation, manifest update, and
  post-verification.
- DRY findings: ID validation, JSON schemas, external-directory checks, hashing, Git execution, and
  patch capture are centralized. The shared tracked-only inventory and shared patch capture cause the
  same evidence-loss defects consistently rather than duplicating them.
- Defects: `_hash_tree` inventories only `git ls-files`, so added untracked memory or governance files
  are excluded from baseline/run verification even though they can change controlled behavior.
  `_capture_patch` uses `git diff --binary HEAD`, which omits untracked files; reset/archive then remove
  the worktree and permanently lose that evidence. Reset writes its numbered patch before worktree
  removal, but does not roll it back or advance state when removal fails, permanently poisoning the
  next retry. Finally, reset validates only the baseline-manifest file checksum before deletion; if
  baseline and run metadata are tampered consistently, the content mismatch is discovered only after
  destructive remove/recreate, so the original run state is lost despite the failing reset.
- Commands executed: Ruff format check, Ruff lint, mypy, full pytest, focused disposable-Git
  lifecycle tests, full P07 diff inspection, and diff check. Standard gates passed with `138 passed`;
  expanded real lifecycle attacks produced `5 failed, 8 passed`, covering all four defects above.
- Round 2 clean checkout: detached reviewer worktree at
  `7546865e3380c12d916715929a88357048c69a3a`; clean before re-review.
- Round 2 diff inspected: bounded three-file fix delta from rejected commit `df80c3c` contains only
  baseline verification, transactional run-evidence handling, and tracker evidence; no P08 scope.
- Round 2 counterexamples: verification now rejects an untracked controlled memory; reset and archive
  patches retain untracked application evidence; a locked worktree removal removes its temporary
  reservation so reset succeeds after unlock; coordinated baseline/run-manifest tampering fails before
  the modified worktree is replaced.
- Round 2 SOLID/DRY findings: commit/tree verification and working-tree verification remain distinct
  baseline operations, while one staged patch path handles tracked/untracked evidence and failure
  cleanup for both reset and archive. Lifecycle ownership remains in the run-control modules.
- Round 2 commands executed: focused disposable-Git lifecycle tests, Ruff format check (`43 files`),
  Ruff lint, mypy (`43 source files`), full pytest, and fix-delta diff check. All passed.

### Verdict

PASS

## P08 — Client launch isolation

Status: READY_FOR_REVIEW
Implementer commit: HEAD (resolved to the commit supplied for review)

### Acceptance criteria

- Controlled Claude launches set `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
- Controlled Codex launches use a fresh isolated `CODEX_HOME` with local memory disabled.
- Both clients start in the named detached run worktree and use only its committed project hooks.
- Launch configuration and artifacts live outside the baseline and run worktrees.
- Tests detect inherited native memory, reused client homes, cross-run contamination, unsafe environment overrides, and false rejection of clean isolation.

### Implementer evidence

- Files changed: `src/lab/runs/launch.py`, `src/lab/cli.py`,
  `tests/integration/test_run_lifecycle.py`, and this tracker.
- Commands executed: official Codex memory/config documentation lookup; Ruff format/check; mypy;
  focused launch-isolation pytest; full pytest; CLI dry-run coverage; `git diff --check`.
- Results: Ruff format `44 files already formatted`; Ruff lint `All checks passed!`; mypy `Success:
  no issues found in 44 source files`; focused launch isolation `9 passed, 13 deselected in 34.61s`;
  full pytest `152 passed in 85.02s`; diff check passed.
- Coverage: plans pin cwd to the verified named detached worktree and pass argv without a shell;
  reserved inherited memory/home/mode values are removed and caller overrides reject; Claude gets
  auto-memory disabled plus a fresh external config directory; Codex gets a unique external home
  with memory feature/use/generation disabled and only the verified project trusted; external launch
  records expose only controlled environment values. Tests cover two-run home uniqueness, state
  reuse, forged path redirection, symlinked state, modified project hooks, safe environment additions,
  a fake runner, and dry planning without either client installed.
- Re-review fixes: Codex cwd/config/profile/feature overrides and Claude settings/session/directory
  overrides reject across short, attached, long, and equals forms while prompt text after `--`
  remains valid; launch execution revalidates arguments, mode, memory disablement, isolated home,
  executable, paths, and cross-client state against the fresh run manifest; spawn/runner exceptions
  remove only the newly created client home, config, record, and partial logs so a clean retry works.
- Re-review results: focused argument/mode/rollback regressions `2 passed in 8.73s`; Ruff format `44
  files already formatted`; Ruff lint `All checks passed!`; mypy `Success: no issues found in 44
  source files`; full pytest `154 passed in 88.15s`; diff check passed.

### Adversarial review

- Clean checkout: detached reviewer worktree at
  `4b4df3a6eeec7081266428319a7c7510696c2638`; clean before review.
- Diff inspected: complete four-file P08 delta from the accepted P07 review, covering launch-plan
  construction/execution, CLI composition, disposable-run tests, and tracker. No P09 canary,
  experiment task, seeded failure, metric, or result was added.
- Counterexamples: a verified block run accepts Codex arguments `-C /tmp -c
  features.memories=true`, allowing the client to replace both the verified working root and the
  memory-disabled config. A forged/stale plan for the same block run passes launch-time verification
  with `LAB_GOVERNANCE_MODE=audit`, and the fake runner receives audit mode. A runner `OSError` occurs
  after the Claude client directory is created; the next clean attempt is rejected because that state
  already exists. Existing two-run uniqueness, inherited-env sanitation, project-hook verification,
  symlink/redirection rejection, and permission-neutral fake-runner controls pass.
- SOLID findings: launch planning/execution has one run-control owner and the CLI only composes it;
  subprocess execution uses fixed argv, explicit cwd/env, and no shell. However, invariants are
  enforced only while building a mutable public `LaunchPlan`, not completely at the execution
  boundary, and state preparation is not recoverable when execution fails.
- DRY findings: reserved environment keys, path derivation, state preparation, launch records, and
  subprocess execution are centralized. Both clients share the same missing launch-time mode/argument
  validation and failure cleanup rather than duplicating policy.
- Defects: unrestricted client arguments can override Codex cwd and memory configuration, defeating
  the two primary isolation guarantees. `launch_client` re-verifies the run path but does not require
  the plan's `LAB_GOVERNANCE_MODE` to equal the current run mode, so block governance can be downgraded
  to audit after planning. Finally, client state is created before runner success and is not rolled
  back on spawn/runner failure, permanently false-rejecting a retry for an otherwise clean run.
- Commands executed: focused launch-isolation pytest, Ruff format check, Ruff lint, mypy, full pytest,
  full P08 diff inspection, diff check, local Codex CLI option inspection, and a disposable-run direct
  launch probe. Standard/focused gates passed; the direct probe reproduced all three defects.
- Round 2 clean checkout: detached reviewer worktree at
  `5b5d6dad90ef23a224337b9d9d69a897125bcc69`; clean before re-review.
- Round 2 diff inspected: bounded three-file fix delta from rejected commit `4b4df3a` contains only
  launch invariant validation/rollback, focused regressions, and tracker evidence; no P09 scope.
- Round 2 counterexamples: Codex cwd/config/profile/feature and Claude settings/session/directory
  override forms now reject at planning and launch boundaries; a plan with audit mode for a verified
  block run rejects; runner failure removes the newly created state and partial logs, then the same
  clean launch plan succeeds on retry.
- Round 2 SOLID/DRY findings: one client-argument validator is reused at plan and execution boundaries,
  and one rollback path owns cleanup for both clients. Exact cwd/home/mode/path invariants are checked
  immediately before the runner without moving policy into the CLI.
- Round 2 commands executed: focused argument/mode/rollback regressions (`2 passed`), Ruff format
  check (`44 files`), Ruff lint, mypy (`44 source files`), full pytest, and fix-delta diff check. All
  passed.

### Verdict

PASS

## P09 — End-to-end canary

Status: READY_FOR_REVIEW
Implementer commit: HEAD (resolved to the commit supplied for review)

### Acceptance criteria

- The base order service, memory validation/retrieval/rendering, shared hooks, protection checks, baseline lifecycle, and isolated launch flow work together from a frozen clean baseline.
- The same prompt injects equivalent memory context in Claude and Codex.
- Prompt injection cannot bypass protected edit denial or destructive-command denial.
- A failing canary governance check allows completion in `audit` and rejects Stop in `block` until resolved.
- Archive preserves evidence, three resets reproduce exact baseline hashes, and native/client memory does not leak across runs.
- Every P01-P08 item has an independent reviewer `PASS`; no experiment task, seeded violation, measurement, result, or conclusion is present.

### Implementer evidence

- Files changed: `tests/adversarial/test_platform_canary.py` and this tracker. No production
  experiment task, seeded architecture violation, metric, result, or conclusion was added.
- Commands executed: focused adversarial canary pytest; Ruff format/check; mypy; full pytest; `git
  diff --check`.
- Results: focused canary `2 passed in 18.83s`; Ruff format `45 files already formatted`; Ruff lint
  `All checks passed!`; mypy `Success: no issues found in 45 source files`; full pytest `156 passed
  in 104.80s`; diff check passed.
- Coverage: a disposable clean Git baseline runs the frozen SQLite order CLI and validates governed
  Markdown memory; Claude and Codex render identical ID/authority/content context; an injection asking
  to ignore policy, edit hooks, and reset Git remains denied by both adapters; a test-only temporary
  check logs/allows in audit, blocks in block, and then allows when resolved; fake launches verify
  Claude/Codex memory isolation and separate Codex homes; three resets reproduce identical
  commit/tree/manifest hashes; archive retains reset/final patches, transcript, log, launch records,
  and the isolated memory marker. A separate gate requires independent `PASS` verdicts for P01-P08.

### Adversarial review

- Clean checkout:
- Diff inspected:
- Counterexamples:
- SOLID findings:
- DRY findings:
- Commands executed:

### Verdict

PENDING
