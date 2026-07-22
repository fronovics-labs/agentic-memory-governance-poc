# Agentic memory governance POC

This repository is the Part 1 experimental platform: a small order service plus a governed,
client-neutral memory and hook layer for Claude Code and Codex. It makes memory selection,
governance decisions, baselines, isolated runs, and run evidence explicit and reproducible.

It is intentionally not a web service, an agent plugin framework, an ORM-based application, or a
vector-search system. Part 1 also contains no experimental tasks, seeded violations, measurements,
results, or conclusions.

## Prerequisites and setup

- Git
- [uv](https://docs.astral.sh/uv/)
- Python 3.12 (uv can install the pinned interpreter)
- `claude` or `codex` on `PATH` only when performing a real client launch

Install the locked development environment:

```bash
uv sync --frozen --dev
```

The required repository checks are:

```bash
uv run ruff check .
uv run mypy
uv run pytest
```

## Try the synthetic order service

The CLI composes the application service with a SQLite repository. Separate invocations use the
same database, so they also demonstrate persistence.

```bash
uv run python -m sample_app.cli --database /tmp/orders.sqlite3 create --id order-001 --item adapter --quantity 2
uv run python -m sample_app.cli --database /tmp/orders.sqlite3 get --id order-001
uv run python -m sample_app.cli --database /tmp/orders.sqlite3 list
```

## Define and retrieve governed memory

Memories are Markdown files in `.org-memory/items/` with TOML front matter. Every memory must
provide all fields shown here, including empty optional values:

```toml
+++
id = "POLICY-001"
type = "policy"
authority = "mandatory"
status = "active"
scopes = ["sample_app/**"]
owner = "platform"
source_ids = []
enforcement_ids = []
valid_from = ""
valid_until = ""
supersedes = ""
+++

Order changes must preserve deterministic repository behavior.
```

Validate the corpus, search it deterministically, or render path-scoped context for a prompt:

```bash
uv run lab memory validate
uv run lab memory search --query "order repository"
uv run lab memory context --prompt "change order persistence" --path sample_app/application/orders.py
```

`context` accepts a normalized repository-relative path, applies the memory scopes, and renders
selected entries as `[ID | authority] body`. Retrieval and rendering stay separate from Markdown
storage and from governance enforcement.

## Components and request flow

1. `sample_app/` contains the synthetic domain, application service, SQLite adapter, and CLI.
2. `src/lab/memory/` parses, validates, stores, retrieves, and renders governed memories.
3. A shared core in `src/lab/hooks/` handles prompt, pre-tool, and stop events; the Claude and
   Codex adapters only translate client JSON.
4. `src/lab/governance/` evaluates protected paths and registered checks. Protected pre-tool
   writes are always rejected. At stop, `audit` reports violations but allows completion, while
   `block` rejects completion until the violation is fixed.
5. `src/lab/runs/` freezes baselines, creates detached worktrees, launches clients, and stores
   evidence outside the source repository.

The committed `.claude/settings.json` and `.codex/hooks.json` connect both clients to the same
`UserPromptSubmit`, `PreToolUse`, and `Stop` lifecycle. Prompt hooks retrieve and render memory;
pre-tool hooks protect governance files and destructive baseline operations; stop hooks run the
registered checks.

## Freeze and verify a clean baseline

Freezing requires a clean Git worktree and makes the named baseline active:

```bash
uv run lab baseline freeze --name platform-v1
uv run lab baseline verify --name platform-v1
```

The manifest pins the Git commit and tree plus hashes for `uv.lock`, governed memories, hook and
governance configuration, and platform files. It also records the Python and host platform.

## Manage isolated runs

Run creation uses the active baseline and creates a named detached worktree. Verification checks
that identity and configuration; reset captures a patch before recreating the worktree.

```bash
uv run lab run create --id run-001 --mode block
uv run lab run verify --id run-001
uv run lab run reset --id run-001
```

Mutable artifacts never live in the source repository. For a repository named `<repo>`, they are
written to the sibling `<repo>-runs/` directory:

```text
<repo>-runs/
├── baselines/
└── runs/run-001/
    ├── worktree/
    ├── run.json
    └── artifacts/
        ├── {logs,transcripts,patches}/
        └── clients/<client>/{home,launch.json}
```

## Launch Claude Code or Codex

Dry-run first to inspect the launch plan without requiring the client binary:

```bash
uv run lab run launch --id run-001 --client codex --dry-run
uv run lab run launch --id run-001 --client claude --dry-run
```

Real launches use the same command without `--dry-run`:

```bash
uv run lab run launch --id run-001 --client codex
uv run lab run launch --id run-001 --client claude
```

The launcher verifies the run and starts the client in its detached worktree with the committed
project hooks and the run's governance mode. Claude gets a fresh external `CLAUDE_CONFIG_DIR` and
`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. Codex gets a fresh external `CODEX_HOME` whose configuration
disables native memories and trusts only the run project. Reserved environment, working-directory,
profile, config, and memory overrides are rejected; per-run client state is not reused.

After dry-run inspection or a real client session, archive the run as the final cleanup step. This
captures its final patch and removes its detached worktree:

```bash
uv run lab run archive --id run-001
```

An archived run is final evidence and cannot be verified, reset, or launched again.

## Project map

- `sample_app/` — synthetic order service
- `src/lab/memory/` — Markdown/TOML memory model, repository, retrieval, and context
- `src/lab/hooks/` — shared hook core and thin client adapters
- `src/lab/governance/` — protected-path and registered-check policy
- `src/lab/runs/` — baseline, lifecycle, artifact, and client-launch isolation
- `tests/` — unit, contract, integration, and end-to-end checks

See [ARCHITECTURE.md](ARCHITECTURE.md) for ownership and dependency boundaries and
[TASKS.md](TASKS.md) for the reviewed Part 1 build record.
