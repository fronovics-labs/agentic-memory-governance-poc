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

### Verdict

CHANGES_REQUESTED

## P05 — Governance engine

Status: NOT_STARTED
Implementer commit: —

### Acceptance criteria

- Checks implement the documented protocol and register without editing the engine.
- `audit` records every violation and allows completion; `block` returns every violation and rejects completion.
- One failing or crashing check cannot suppress another check's result.
- Platform checks protect `.org-memory/`, hook configuration, governance checks, and baseline manifests, and run formatting, types, and tests before completion.
- No concrete check import, central type conditional, experiment-specific architectural check, or duplicated business rule exists in the engine.

### Implementer evidence

- Files changed:
- Commands executed:
- Results:

### Adversarial review

- Clean checkout:
- Diff inspected:
- Counterexamples:
- SOLID findings:
- DRY findings:
- Commands executed:

### Verdict

PENDING

## P06 — Claude and Codex adapters

Status: NOT_STARTED
Implementer commit: —

### Acceptance criteria

- One shared core implements `UserPromptSubmit`, `PreToolUse`, and `Stop` behavior for both clients.
- Prompt submission injects the same applicable memory IDs, authority levels, and content through each client's JSON shape.
- Pre-tool handling blocks protected writes and destructive reset/baseline commands while allowing adjacent safe operations.
- Stop handling logs and allows in `audit`, and reports and continues work in `block`.
- Adapters contain only input/output translation; parity, malformed-input, false-acceptance, and false-rejection contract tests cover both clients.

### Implementer evidence

- Files changed:
- Commands executed:
- Results:

### Adversarial review

- Clean checkout:
- Diff inspected:
- Counterexamples:
- SOLID findings:
- DRY findings:
- Commands executed:

### Verdict

PENDING

## P07 — Baseline, worktree and reset lifecycle

Status: NOT_STARTED
Implementer commit: —

### Acceptance criteria

- `lab baseline freeze/verify --name NAME` records and verifies Git commit/tree, lock, memory, hook, governance-check, Python, and platform hashes.
- `lab run create --id ID --mode audit|block` creates a detached worktree from the frozen commit in the sibling runs directory.
- Reset deletes only the named run worktree, recreates it from the frozen commit, verifies every baseline hash, preserves external transcripts/logs/patches, and fails closed on mismatch.
- `lab run verify` and `lab run archive` are deterministic and reject unsafe IDs or paths.
- Dirty state, symlink/path escape, manifest tampering, failed reset, unrelated worktree preservation, and three consecutive identical resets are tested.

### Implementer evidence

- Files changed:
- Commands executed:
- Results:

### Adversarial review

- Clean checkout:
- Diff inspected:
- Counterexamples:
- SOLID findings:
- DRY findings:
- Commands executed:

### Verdict

PENDING

## P08 — Client launch isolation

Status: NOT_STARTED
Implementer commit: —

### Acceptance criteria

- Controlled Claude launches set `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
- Controlled Codex launches use a fresh isolated `CODEX_HOME` with local memory disabled.
- Both clients start in the named detached run worktree and use only its committed project hooks.
- Launch configuration and artifacts live outside the baseline and run worktrees.
- Tests detect inherited native memory, reused client homes, cross-run contamination, unsafe environment overrides, and false rejection of clean isolation.

### Implementer evidence

- Files changed:
- Commands executed:
- Results:

### Adversarial review

- Clean checkout:
- Diff inspected:
- Counterexamples:
- SOLID findings:
- DRY findings:
- Commands executed:

### Verdict

PENDING

## P09 — End-to-end canary

Status: NOT_STARTED
Implementer commit: —

### Acceptance criteria

- The base order service, memory validation/retrieval/rendering, shared hooks, protection checks, baseline lifecycle, and isolated launch flow work together from a frozen clean baseline.
- The same prompt injects equivalent memory context in Claude and Codex.
- Prompt injection cannot bypass protected edit denial or destructive-command denial.
- A failing canary governance check allows completion in `audit` and rejects Stop in `block` until resolved.
- Archive preserves evidence, three resets reproduce exact baseline hashes, and native/client memory does not leak across runs.
- Every P01-P08 item has an independent reviewer `PASS`; no experiment task, seeded violation, measurement, result, or conclusion is present.

### Implementer evidence

- Files changed:
- Commands executed:
- Results:

### Adversarial review

- Clean checkout:
- Diff inspected:
- Counterexamples:
- SOLID findings:
- DRY findings:
- Commands executed:

### Verdict

PENDING
