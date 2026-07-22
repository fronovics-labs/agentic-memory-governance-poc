"""External detached-worktree lifecycle for controlled runs."""

import subprocess
from dataclasses import replace
from pathlib import Path

from lab.runs.baseline import (
    active_baseline_name,
    baseline_path,
    load_baseline,
    validate_runs_root,
    verify_baseline,
    verify_frozen_commit,
    verify_frozen_tree,
)
from lab.runs.manifest import (
    BaselineManifest,
    RunManifest,
    RunMode,
    read_json,
    safe_directory,
    sha256_file,
    validate_id,
    write_json,
)


def create_run(root: Path, runs_root: Path, run_id: str, mode: RunMode) -> Path:
    validate_id(run_id, "run ID")
    if mode not in ("audit", "block"):
        raise ValueError(f"unsupported governance mode: {mode}")
    validate_runs_root(root, runs_root)
    name = active_baseline_name(runs_root)
    baseline = verify_baseline(root, runs_root, name)
    run_dir = _run_dir(runs_root, run_id)
    if run_dir.exists() or run_dir.is_symlink():
        raise ValueError(f"run already exists: {run_id}")
    artifacts = run_dir / "artifacts"
    for directory in ("logs", "transcripts", "patches"):
        (artifacts / directory).mkdir(parents=True, exist_ok=True)
    worktree = run_dir / "worktree"
    _git(root, "worktree", "add", "--detach", str(worktree), baseline.git_commit)
    manifest = RunManifest(
        run_id=run_id,
        mode=mode,
        status="active",
        baseline_name=name,
        baseline_manifest_sha256=sha256_file(baseline_path(runs_root, name)),
        repository_root=str(root.resolve()),
        worktree=str(worktree.resolve()),
    )
    write_json(run_dir / "run.json", manifest.to_dict())
    try:
        _verify_run(root, runs_root, manifest)
    except Exception:
        _git(root, "worktree", "remove", "--force", str(worktree))
        raise
    return worktree


def verify_run(root: Path, runs_root: Path, run_id: str) -> RunManifest:
    manifest = _load_run(root, runs_root, run_id)
    _verify_run(root, runs_root, manifest)
    return manifest


def reset_run(root: Path, runs_root: Path, run_id: str) -> Path:
    manifest = _load_run(root, runs_root, run_id)
    baseline = _verify_run(root, runs_root, manifest)
    worktree = Path(manifest.worktree)
    run_dir = _run_dir(runs_root, run_id)
    sequence = manifest.reset_count + 1
    temporary, final = _stage_patch(worktree, run_dir, sequence)
    removed = False
    try:
        _git(root, "worktree", "remove", "--force", str(worktree))
        removed = True
        _git(root, "worktree", "add", "--detach", str(worktree), baseline.git_commit)
        updated = replace(manifest, reset_count=sequence)
        _verify_run(root, runs_root, updated)
        temporary.replace(final)
        write_json(run_dir / "run.json", updated.to_dict())
    except Exception:
        _finish_failed_patch(temporary, run_dir, sequence, removed)
        raise
    return worktree


def archive_run(root: Path, runs_root: Path, run_id: str) -> Path:
    manifest = _load_run(root, runs_root, run_id)
    _verify_run(root, runs_root, manifest)
    worktree = Path(manifest.worktree)
    run_dir = _run_dir(runs_root, run_id)
    sequence = manifest.reset_count + 1
    temporary, final = _stage_patch(worktree, run_dir, sequence, prefix="archive")
    try:
        _git(root, "worktree", "remove", "--force", str(worktree))
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    temporary.replace(final)
    write_json(run_dir / "run.json", replace(manifest, status="archived").to_dict())
    return final


def _verify_run(root: Path, runs_root: Path, manifest: RunManifest) -> BaselineManifest:
    _require_active(manifest)
    baseline = _verified_manifest(runs_root, manifest)
    verify_frozen_commit(root, baseline)
    worktree = Path(manifest.worktree)
    if not worktree.is_dir() or worktree.is_symlink():
        raise ValueError("run worktree is missing or unsafe")
    if _git(worktree, "rev-parse", "HEAD") != baseline.git_commit:
        raise ValueError("run commit does not match the frozen baseline")
    if _git(worktree, "rev-parse", "HEAD^{tree}") != baseline.git_tree:
        raise ValueError("run tree does not match the frozen baseline")
    verify_frozen_tree(worktree, baseline)
    return baseline


def _verified_manifest(runs_root: Path, run: RunManifest) -> BaselineManifest:
    path = baseline_path(runs_root, run.baseline_name)
    if sha256_file(path) != run.baseline_manifest_sha256:
        raise ValueError("baseline manifest was modified after run creation")
    return load_baseline(runs_root, run.baseline_name)


def _load_run(root: Path, runs_root: Path, run_id: str) -> RunManifest:
    validate_id(run_id, "run ID")
    validate_runs_root(root, runs_root)
    run_dir = _run_dir(runs_root, run_id)
    if run_dir.is_symlink():
        raise ValueError("run directory must not be a symlink")
    manifest = RunManifest.from_dict(read_json(run_dir / "run.json"))
    expected_worktree = (run_dir / "worktree").resolve()
    if (
        Path(manifest.repository_root) != root.resolve()
        or Path(manifest.worktree) != expected_worktree
    ):
        raise ValueError("run manifest paths do not match the selected run")
    return manifest


def _stage_patch(
    worktree: Path,
    run_dir: Path,
    sequence: int,
    *,
    prefix: str = "reset",
) -> tuple[Path, Path]:
    patches = safe_directory(run_dir, "artifacts", "patches")
    final = patches / f"{prefix}-{sequence:04d}.patch"
    temporary = patches / f".{prefix}-{sequence:04d}.patch.tmp"
    if any(path.exists() or path.is_symlink() for path in (final, temporary)):
        raise ValueError(f"patch evidence already exists: {final}")
    temporary.write_text(_patch_content(worktree), encoding="utf-8")
    return temporary, final


def _patch_content(worktree: Path) -> str:
    parts = [_git(worktree, "diff", "--binary", "HEAD", keep_newline=True)]
    untracked = _git(
        worktree,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        keep_newline=True,
    ).split("\0")
    for relative in sorted(path for path in untracked if path):
        path = worktree / relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(worktree):
            raise ValueError(f"unsafe untracked evidence path: {relative}")
        completed = subprocess.run(
            ("git", "diff", "--binary", "--no-index", "--", "/dev/null", relative),
            cwd=worktree,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode not in (0, 1):
            raise ValueError(completed.stderr.strip() or "could not capture untracked evidence")
        parts.append(completed.stdout)
    return "".join(parts)


def _finish_failed_patch(temporary: Path, run_dir: Path, sequence: int, removed: bool) -> None:
    if not removed:
        temporary.unlink(missing_ok=True)
        return
    failed = safe_directory(run_dir, "artifacts", "patches") / f"failed-reset-{sequence:04d}.patch"
    if failed.exists() or failed.is_symlink():
        raise ValueError(f"failed reset evidence already exists: {failed}")
    temporary.replace(failed)


def _require_active(manifest: RunManifest) -> None:
    if manifest.status != "active":
        raise ValueError(f"run is not active: {manifest.run_id}")


def _run_dir(runs_root: Path, run_id: str) -> Path:
    return safe_directory(runs_root, "runs", run_id)


def _git(root: Path, *arguments: str, keep_newline: bool = False) -> str:
    completed = subprocess.run(
        ("git", "-C", str(root), *arguments),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "Git command failed")
    return completed.stdout if keep_newline else completed.stdout.strip()
