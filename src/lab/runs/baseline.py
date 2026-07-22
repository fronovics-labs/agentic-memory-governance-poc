"""Baseline freeze and verification."""

import platform as runtime_platform
import hashlib
import subprocess
from pathlib import Path

from lab.runs.manifest import (
    BaselineManifest,
    read_json,
    safe_directory,
    sha256_file,
    validate_id,
    write_json,
)

PLATFORM_CONFIG_FILES = (
    ".python-version",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "CLAUDE.md",
    "pyproject.toml",
    "scripts/lab",
    "src/lab/cli.py",
)


def repository_root(cwd: str | Path = ".") -> Path:
    root = _git(Path(cwd), "rev-parse", "--show-toplevel")
    return Path(root).resolve()


def default_runs_root(root: Path) -> Path:
    return root.parent / f"{root.name}-runs"


def freeze_baseline(root: Path, runs_root: Path, name: str) -> Path:
    validate_id(name, "baseline name")
    _require_clean(root)
    _validate_runs_root(root, runs_root)
    manifest = _capture(root, name)
    verify_frozen_commit(root, manifest)
    safe_directory(runs_root, "baselines")
    path = _baseline_path(runs_root, name)
    if path.exists() or path.is_symlink():
        raise ValueError(f"baseline already exists: {name}")
    write_json(path, manifest.to_dict())
    write_json(runs_root / "baselines" / "active.json", {"name": name})
    return path


def verify_baseline(root: Path, runs_root: Path, name: str) -> BaselineManifest:
    validate_id(name, "baseline name")
    _validate_runs_root(root, runs_root)
    manifest = load_baseline(runs_root, name)
    verify_frozen_commit(root, manifest)
    verify_frozen_tree(root, manifest)
    return manifest


def verify_frozen_tree(root: Path, manifest: BaselineManifest) -> None:
    actual = _capture(root, manifest.name)
    if actual != manifest:
        raise ValueError("baseline verification failed: repository does not match manifest")


def verify_frozen_commit(root: Path, manifest: BaselineManifest) -> None:
    actual = BaselineManifest(
        name=manifest.name,
        git_commit=manifest.git_commit,
        git_tree=_git(root, "rev-parse", f"{manifest.git_commit}^{{tree}}"),
        python_version=runtime_platform.python_version(),
        platform=f"{runtime_platform.system()}-{runtime_platform.machine()}",
        dependency_lock=_hash_git_file(root, manifest.git_commit, "uv.lock"),
        memories=_hash_git_tree(root, manifest.git_commit, ".org-memory"),
        hooks=_hash_git_files(
            root,
            manifest.git_commit,
            (".claude/settings.json", ".codex/hooks.json"),
        ),
        governance_checks=_hash_git_tree(root, manifest.git_commit, "src/lab/governance/checks"),
        platform_config=_hash_git_files(root, manifest.git_commit, PLATFORM_CONFIG_FILES)
        | _hash_git_tree(root, manifest.git_commit, "agents"),
    )
    if actual != manifest:
        raise ValueError("baseline manifest does not match its frozen Git commit")


def load_baseline(runs_root: Path, name: str) -> BaselineManifest:
    validate_id(name, "baseline name")
    safe_directory(runs_root, "baselines")
    return BaselineManifest.from_dict(read_json(_baseline_path(runs_root, name)))


def active_baseline_name(runs_root: Path) -> str:
    safe_directory(runs_root, "baselines")
    value = read_json(runs_root / "baselines" / "active.json")
    if set(value) != {"name"}:
        raise ValueError("active baseline pointer is malformed")
    return validate_id(value["name"], "baseline name")


def baseline_path(runs_root: Path, name: str) -> Path:
    validate_id(name, "baseline name")
    safe_directory(runs_root, "baselines")
    return _baseline_path(runs_root, name)


def validate_runs_root(root: Path, runs_root: Path) -> None:
    _validate_runs_root(root, runs_root)


def _capture(root: Path, name: str) -> BaselineManifest:
    return BaselineManifest(
        name=name,
        git_commit=_git(root, "rev-parse", "HEAD"),
        git_tree=_git(root, "rev-parse", "HEAD^{tree}"),
        python_version=runtime_platform.python_version(),
        platform=f"{runtime_platform.system()}-{runtime_platform.machine()}",
        dependency_lock=sha256_file(root / "uv.lock"),
        memories=_hash_tree(root, ".org-memory"),
        hooks=_hash_files(root, (".claude/settings.json", ".codex/hooks.json")),
        governance_checks=_hash_tree(root, "src/lab/governance/checks"),
        platform_config=_hash_files(root, PLATFORM_CONFIG_FILES) | _hash_tree(root, "agents"),
    )


def _hash_tree(root: Path, directory: str) -> dict[str, str]:
    base = root / directory
    if base.is_symlink() or not base.is_dir():
        raise ValueError(f"expected a regular directory: {base}")
    files = sorted(
        path
        for path in base.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in (".pyc", ".pyo")
    )
    return _hash_files(root, tuple(path.relative_to(root).as_posix() for path in files))


def _hash_files(root: Path, paths: tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in paths:
        path = root / relative
        hashes[relative] = sha256_file(path)
    return hashes


def _hash_git_tree(root: Path, commit: str, directory: str) -> dict[str, str]:
    paths = tuple(
        path
        for path in _git(root, "ls-tree", "-r", "--name-only", commit, "--", directory).splitlines()
        if "__pycache__" not in Path(path).parts and Path(path).suffix not in (".pyc", ".pyo")
    )
    return _hash_git_files(root, commit, paths)


def _hash_git_files(root: Path, commit: str, paths: tuple[str, ...]) -> dict[str, str]:
    return {path: _hash_git_file(root, commit, path) for path in paths}


def _hash_git_file(root: Path, commit: str, path: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(root), "show", f"{commit}:{path}"),
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise ValueError(completed.stderr.decode(errors="replace").strip() or "Git show failed")
    return hashlib.sha256(completed.stdout).hexdigest()


def _require_clean(root: Path) -> None:
    if _git(root, "status", "--porcelain"):
        raise ValueError("baseline freeze requires a clean Git worktree")


def _validate_runs_root(root: Path, runs_root: Path) -> None:
    root = root.resolve()
    absolute = runs_root.absolute()
    for path in (*reversed(absolute.parents), absolute):
        if path.is_symlink():
            raise ValueError(f"runs directory has a symlinked ancestor: {path}")
    resolved = absolute.resolve()
    if resolved.parent != root.parent or resolved == root:
        raise ValueError("runs directory must be an external sibling of the repository")


def _baseline_path(runs_root: Path, name: str) -> Path:
    return runs_root / "baselines" / f"{name}.json"


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(root), *arguments),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "Git command failed")
    return completed.stdout.strip()
