# Architecture contract

This repository is the experimental platform. It contains no experiment tasks, seeded
violations, measurements, or conclusions.

## Boundaries and ownership

| Path | Responsibility | Owner |
| --- | --- | --- |
| `sample_app/domain/` | Order entities and business rules; no application, infrastructure, or lab imports | Application |
| `sample_app/application/` | Use cases and repository ports; may depend only on the domain | Application |
| `sample_app/infrastructure/` | SQLite repository adapters; may depend on application ports and domain types | Application |
| `sample_app/cli.py` | Synthetic-app composition root and user-facing CLI | Application |
| `src/lab/memory/` | Memory metadata, storage port/Markdown adapter, retrieval, and rendering | Memory |
| `src/lab/governance/` | Check contracts, engine, and platform-protection checks | Governance |
| `src/lab/hooks/core.py` | Client-neutral hook behavior | Governance |
| `src/lab/hooks/*_adapter.py` | JSON translation only; no retrieval or governance rules | Client integration |
| `src/lab/runs/` | Frozen baselines, external run worktrees, manifests, reset, and isolation | Run control |
| `scripts/lab`, `src/lab/cli.py`, `src/lab/__main__.py` | Platform command bootstrap and subcommand composition; delegates behavior to owning modules | Platform integration |
| `.org-memory/items/` | Governed Markdown memory records | Architecture |
| `.claude/`, `.codex/` | Thin client hook configuration | Client integration |
| `agents/` | Implementer and independent reviewer operating contracts | Architecture |
| `tests/` | Unit, contract, integration, and adversarial verification | Matching production owner |

## Dependency rules

1. Dependencies point inward: infrastructure -> application -> domain.
2. The lab may operate on the sample application, but the sample application never imports the lab.
3. Memory retrieval depends on a repository port, not filesystem details. Parsing, retrieval,
   rendering, and governance remain separate modules.
4. Governance checks implement one small protocol. The engine registers checks and never imports
   concrete check classes; adding a check does not edit an engine conditional.
5. Claude and Codex adapters translate client JSON and delegate all behavior to the shared hook
   core. Business rules appear once.
6. Run worktrees are disposable. Transcripts, logs, patches, and manifests live in a sibling
   `memory-governance-lab-runs/` directory, never inside a run worktree.

## Protected platform surface

During controlled runs, writes to these paths are forbidden:

- `.org-memory/`
- `.claude/settings.json`
- `.codex/hooks.json`
- `src/lab/governance/checks/`
- the selected frozen baseline manifest

Reset and baseline-destroying commands are also forbidden from inside a controlled run. P05-P07
implement these protections; P01 only defines the contract.

## Runtime contracts

- Python is exactly the 3.12 series.
- SQLite is the synthetic application's persistence mechanism.
- Memories are Markdown files with TOML front matter and deterministic path/keyword retrieval.
- Governance modes are `audit` (record and allow) and `block` (report and reject completion).
- Native Claude and Codex memory is disabled for controlled runs.
- Baselines identify a Git commit and tree plus dependency, memory, hook, check, Python, and platform
  hashes. Reset recreates only the named run and fails on any mismatch.

## Deliberate non-goals for Part 1

No web API, dependency injection framework, ORM, embeddings, vector database, custom plugin system,
or experiment-specific architecture check belongs in this platform. Add one only when a later
accepted task explicitly requires it.
