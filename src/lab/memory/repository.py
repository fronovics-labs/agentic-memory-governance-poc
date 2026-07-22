"""Safe filesystem repository for Markdown memories."""

from pathlib import Path

from lab.memory.model import Memory, parse_memory, render_memory, validate_collection


class MarkdownMemoryRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def load_all(self) -> list[Memory]:
        return [self._read(path) for path in self._paths()]

    def save(self, memory: Memory) -> Path:
        self._check_root(require_exists=False)
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{memory.id}.md"
        if path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError(f"unsafe memory path: {path}")
        path.write_text(render_memory(memory), encoding="utf-8")
        return path

    def validate(self) -> tuple[int, list[str]]:
        try:
            paths = self._paths()
        except ValueError as error:
            return 0, [str(error)]

        memories: list[Memory] = []
        errors: list[str] = []
        for path in paths:
            try:
                memories.append(self._read(path))
            except (OSError, ValueError) as error:
                errors.append(str(error))
        errors.extend(validate_collection(memories))
        return len(memories), errors

    def _paths(self) -> list[Path]:
        self._check_root(require_exists=True)
        root = self.root.resolve()
        paths = sorted(
            self.root.rglob("*.md"), key=lambda path: path.relative_to(self.root).as_posix()
        )
        for path in paths:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError(f"unsafe memory path: {path}")
        return paths

    def _check_root(self, *, require_exists: bool) -> None:
        absolute = self.root.absolute()
        for path in (*reversed(absolute.parents), absolute):
            if path.is_symlink():
                raise ValueError(
                    f"unsafe memory directory: {self.root} (symlinked ancestor: {path})"
                )
        if require_exists and not self.root.exists():
            raise ValueError(f"memory directory does not exist: {self.root}")
        if self.root.exists() and not self.root.is_dir():
            raise ValueError(f"unsafe memory directory: {self.root}")

    def _read(self, path: Path) -> Memory:
        try:
            return parse_memory(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            raise ValueError(f"{path.relative_to(self.root).as_posix()}: {error}") from error
