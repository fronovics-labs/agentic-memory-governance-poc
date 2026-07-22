"""Validated, deterministic baseline and run manifests."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

RunMode = Literal["audit", "block"]
RunStatus = Literal["active", "archived"]
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_HASH = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")


def validate_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value) or value in (".", ".."):
        raise ValueError(f"{label} must be a safe identifier")
    return value


def sha256_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_json(path: Path, value: dict[str, object]) -> None:
    if path.is_symlink():
        raise ValueError(f"manifest path must not be a symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_directory(root: Path, *parts: str) -> Path:
    current = root.absolute()
    for part in parts:
        if not part or part in (".", "..") or "/" in part or "\\" in part:
            raise ValueError("unsafe external directory component")
        current /= part
        if current.is_symlink():
            raise ValueError(f"external directory must not be a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"external path must be a directory: {current}")
    return current


def read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected a regular manifest: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid manifest {path}: {error}") from error
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"manifest must contain a JSON object: {path}")
    return value


@dataclass(frozen=True, slots=True)
class BaselineManifest:
    name: str
    git_commit: str
    git_tree: str
    python_version: str
    platform: str
    dependency_lock: str
    memories: dict[str, str]
    hooks: dict[str, str]
    governance_checks: dict[str, str]
    platform_config: dict[str, str]
    schema_version: int = 1

    def __post_init__(self) -> None:
        validate_id(self.name, "baseline name")
        _git_hash(self.git_commit, "Git commit")
        _git_hash(self.git_tree, "Git tree")
        _hash(self.dependency_lock, "dependency lock")
        if not self.python_version or not self.platform:
            raise ValueError("Python version and platform must be non-empty")
        for group in (
            self.memories,
            self.hooks,
            self.governance_checks,
            self.platform_config,
        ):
            _file_hashes(group)
        if self.schema_version != 1:
            raise ValueError("unsupported baseline manifest schema")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BaselineManifest":
        _keys(
            value,
            {
                "name",
                "git_commit",
                "git_tree",
                "python_version",
                "platform",
                "dependency_lock",
                "memories",
                "hooks",
                "governance_checks",
                "platform_config",
                "schema_version",
            },
        )
        try:
            return cls(**value)
        except TypeError as error:
            raise ValueError(f"invalid baseline manifest: {error}") from error


@dataclass(frozen=True, slots=True)
class RunManifest:
    run_id: str
    mode: RunMode
    status: RunStatus
    baseline_name: str
    baseline_manifest_sha256: str
    repository_root: str
    worktree: str
    reset_count: int = 0
    schema_version: int = 1

    def __post_init__(self) -> None:
        validate_id(self.run_id, "run ID")
        validate_id(self.baseline_name, "baseline name")
        if self.mode not in ("audit", "block") or self.status not in ("active", "archived"):
            raise ValueError("invalid run mode or status")
        _hash(self.baseline_manifest_sha256, "baseline manifest")
        if not Path(self.repository_root).is_absolute() or not Path(self.worktree).is_absolute():
            raise ValueError("run paths must be absolute")
        if self.reset_count < 0 or self.schema_version != 1:
            raise ValueError("invalid run manifest version or reset count")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RunManifest":
        _keys(
            value,
            {
                "run_id",
                "mode",
                "status",
                "baseline_name",
                "baseline_manifest_sha256",
                "repository_root",
                "worktree",
                "reset_count",
                "schema_version",
            },
        )
        try:
            return cls(**value)
        except TypeError as error:
            raise ValueError(f"invalid run manifest: {error}") from error


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{label} must be a SHA-256 hash")
    return value


def _git_hash(value: object, label: str) -> str:
    if not isinstance(value, str) or not _GIT_HASH.fullmatch(value):
        raise ValueError(f"{label} must be a Git object hash")
    return value


def _file_hashes(value: object) -> None:
    if not isinstance(value, dict) or any(
        not isinstance(path, str)
        or not path
        or path.startswith("/")
        or "\\" in path
        or any(part in ("", ".", "..") for part in path.split("/"))
        or not isinstance(digest, str)
        or not _SHA256.fullmatch(digest)
        for path, digest in value.items()
    ):
        raise ValueError("file hashes must map safe relative paths to SHA-256 values")


def _keys(value: dict[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValueError("manifest fields do not match the schema")
