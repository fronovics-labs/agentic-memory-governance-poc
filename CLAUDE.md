# Claude Code instructions

Follow `AGENTS.md`, `ARCHITECTURE.md`, and the selected item in `TASKS.md`.

For controlled runs, launch Claude Code with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. Project hooks are
configured in `.claude/settings.json`; client-specific code only translates JSON and delegates to
the shared hook core.
