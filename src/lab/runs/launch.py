"""Deterministic client launch planning and optional subprocess execution."""

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lab.runs.manifest import safe_directory, validate_id, write_json
from lab.runs.workspace import verify_run

Client = Literal["claude", "codex"]
Runner = Callable[["LaunchPlan"], int]
_RESERVED_ENVIRONMENT = {
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY",
    "CLAUDE_CONFIG_DIR",
    "CODEX_HOME",
    "LAB_GOVERNANCE_MODE",
}
_BLOCKED_ARGUMENTS = {
    "claude": {
        "--add-dir",
        "--continue",
        "--plugin-dir",
        "--resume",
        "--setting-sources",
        "--settings",
        "-c",
        "-r",
    },
    "codex": {
        "--cd",
        "--config",
        "--disable",
        "--enable",
        "--profile",
        "-C",
        "-c",
        "-p",
    },
}


@dataclass(frozen=True, slots=True)
class LaunchPlan:
    client: Client
    run_id: str
    repository_root: Path
    runs_root: Path
    cwd: Path
    argv: tuple[str, ...]
    environment: dict[str, str]
    client_home: Path
    stdout_log: Path
    stderr_log: Path
    record_path: Path


def build_launch_plan(
    root: Path,
    runs_root: Path,
    run_id: str,
    client: Client,
    *,
    arguments: Sequence[str] = (),
    base_environment: Mapping[str, str] | None = None,
    environment_overrides: Mapping[str, str] | None = None,
) -> LaunchPlan:
    validate_id(run_id, "run ID")
    if client not in ("claude", "codex"):
        raise ValueError(f"unsupported client: {client}")
    if any(not isinstance(argument, str) or "\0" in argument for argument in arguments):
        raise ValueError("client arguments must be strings without NUL bytes")
    _validate_client_arguments(client, arguments)
    overrides = dict(environment_overrides or {})
    forbidden = sorted(_RESERVED_ENVIRONMENT & overrides.keys())
    if forbidden:
        raise ValueError(f"controlled environment cannot be overridden: {', '.join(forbidden)}")
    if not _valid_environment(overrides):
        raise ValueError("environment overrides must map strings to strings")

    run = verify_run(root, runs_root, run_id)
    worktree = Path(run.worktree)
    run_dir = worktree.parent
    clients = safe_directory(run_dir, "artifacts", "clients")
    client_root = clients / client
    if client_root.is_symlink():
        raise ValueError(f"client launch directory must not be a symlink: {client_root}")
    home = client_root / "home"
    logs = safe_directory(run_dir, "artifacts", "logs")

    environment = dict(os.environ if base_environment is None else base_environment)
    if not _valid_environment(environment):
        raise ValueError("base environment must map valid strings to strings")
    for key in _RESERVED_ENVIRONMENT:
        environment.pop(key, None)
    environment.update(overrides)
    environment["LAB_GOVERNANCE_MODE"] = run.mode
    environment["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    if client == "claude":
        environment["CLAUDE_CONFIG_DIR"] = str(home)
    else:
        environment["CODEX_HOME"] = str(home)

    executable = "claude" if client == "claude" else "codex"
    return LaunchPlan(
        client=client,
        run_id=run_id,
        repository_root=root.resolve(),
        runs_root=runs_root.resolve(),
        cwd=worktree,
        argv=(executable, *arguments),
        environment=environment,
        client_home=home,
        stdout_log=logs / f"{client}.stdout.log",
        stderr_log=logs / f"{client}.stderr.log",
        record_path=client_root / "launch.json",
    )


def launch_client(plan: LaunchPlan, runner: Runner | None = None) -> int:
    run = verify_run(plan.repository_root, plan.runs_root, plan.run_id)
    if Path(run.worktree) != plan.cwd:
        raise ValueError("launch plan does not match the named run worktree")
    _validate_plan(plan, run.mode)
    _require_fresh_destinations(plan)
    try:
        _prepare_client_state(plan)
        exit_code = (runner or _run_subprocess)(plan)
        if not isinstance(exit_code, int):
            raise ValueError("client runner must return an integer exit code")
    except Exception:
        _rollback_client_state(plan)
        raise
    write_json(plan.record_path, _launch_record(plan, exit_code=exit_code))
    return exit_code


def public_plan(plan: LaunchPlan) -> dict[str, object]:
    return _launch_record(plan, exit_code=None)


def _prepare_client_state(plan: LaunchPlan) -> None:
    safe_directory(plan.cwd.parent, "artifacts", "clients")
    client_root = plan.client_home.parent
    if client_root.exists() or client_root.is_symlink():
        raise ValueError(f"client state already exists for run: {plan.run_id}/{plan.client}")
    client_root.mkdir(parents=True)
    plan.client_home.mkdir()
    if plan.client == "codex":
        config = (
            "[features]\n"
            "memories = false\n\n"
            "[memories]\n"
            "use_memories = false\n"
            "generate_memories = false\n\n"
            f"[projects.{json.dumps(str(plan.cwd))}]\n"
            'trust_level = "trusted"\n'
        )
        (plan.client_home / "config.toml").write_text(config, encoding="utf-8")
    write_json(plan.record_path, _launch_record(plan, exit_code=None))


def _launch_record(plan: LaunchPlan, *, exit_code: int | None) -> dict[str, object]:
    controlled_environment = {
        key: plan.environment[key]
        for key in sorted(_RESERVED_ENVIRONMENT)
        if key in plan.environment
    }
    return {
        "argv": list(plan.argv),
        "client": plan.client,
        "client_home": str(plan.client_home),
        "controlled_environment": controlled_environment,
        "cwd": str(plan.cwd),
        "exit_code": exit_code,
        "run_id": plan.run_id,
        "stderr_log": str(plan.stderr_log),
        "stdout_log": str(plan.stdout_log),
    }


def _run_subprocess(plan: LaunchPlan) -> int:
    with (
        plan.stdout_log.open("x", encoding="utf-8") as stdout,
        plan.stderr_log.open("x", encoding="utf-8") as stderr,
    ):
        completed = subprocess.run(
            plan.argv,
            cwd=plan.cwd,
            env=plan.environment,
            stdout=stdout,
            stderr=stderr,
            text=True,
            check=False,
        )
    return completed.returncode


def _validate_plan(plan: LaunchPlan, run_mode: str) -> None:
    run_dir = plan.cwd.parent
    clients = safe_directory(run_dir, "artifacts", "clients")
    logs = safe_directory(run_dir, "artifacts", "logs")
    client_root = clients / plan.client
    expected = (
        client_root / "home",
        logs / f"{plan.client}.stdout.log",
        logs / f"{plan.client}.stderr.log",
        client_root / "launch.json",
    )
    actual = (plan.client_home, plan.stdout_log, plan.stderr_log, plan.record_path)
    if actual != expected or not plan.argv or plan.argv[0] != plan.client:
        raise ValueError("launch plan paths or executable do not match the named client")
    _validate_client_arguments(plan.client, plan.argv[1:])
    if plan.environment.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY") != "1":
        raise ValueError("launch plan does not disable Claude native memory")
    if plan.environment.get("LAB_GOVERNANCE_MODE") != run_mode:
        raise ValueError("launch plan governance mode does not match the named run")
    home_key = "CLAUDE_CONFIG_DIR" if plan.client == "claude" else "CODEX_HOME"
    if plan.environment.get(home_key) != str(plan.client_home):
        raise ValueError("launch plan does not use its isolated client home")
    forbidden_home = "CODEX_HOME" if plan.client == "claude" else "CLAUDE_CONFIG_DIR"
    if forbidden_home in plan.environment:
        raise ValueError("launch plan contains another client's state directory")


def _require_fresh_destinations(plan: LaunchPlan) -> None:
    client_root = plan.client_home.parent
    if client_root.exists() or client_root.is_symlink():
        raise ValueError(f"client state already exists for run: {plan.run_id}/{plan.client}")
    for path in (plan.stdout_log, plan.stderr_log):
        if path.exists() or path.is_symlink():
            raise ValueError(f"client log already exists: {path}")


def _rollback_client_state(plan: LaunchPlan) -> None:
    client_root = plan.client_home.parent
    if client_root.is_symlink():
        client_root.unlink()
    elif client_root.exists():
        shutil.rmtree(client_root)
    for path in (plan.stdout_log, plan.stderr_log):
        if path.exists() or path.is_symlink():
            path.unlink()


def _validate_client_arguments(client: Client, arguments: Sequence[str]) -> None:
    blocked = _BLOCKED_ARGUMENTS[client]
    short = {option for option in blocked if option.startswith("-") and not option.startswith("--")}
    for argument in arguments:
        if argument == "--":
            return
        option = argument.split("=", 1)[0]
        attached = any(
            argument.startswith(candidate) and argument != candidate for candidate in short
        )
        if option in blocked or attached:
            raise ValueError(f"client argument can override controlled launch state: {argument}")


def _valid_environment(environment: Mapping[str, str]) -> bool:
    return all(
        isinstance(key, str)
        and key
        and "=" not in key
        and "\0" not in key
        and isinstance(value, str)
        and "\0" not in value
        for key, value in environment.items()
    )
