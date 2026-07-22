"""Top-level lab command; feature commands are added by their owning tasks."""

import sys
from argparse import ArgumentParser
from collections.abc import Sequence

from lab.memory.repository import MarkdownMemoryRepository


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="lab", description="Agent memory governance laboratory")
    commands = parser.add_subparsers(dest="command", required=True)
    memory = commands.add_parser("memory")
    memory_commands = memory.add_subparsers(dest="memory_command", required=True)
    validate = memory_commands.add_parser("validate")
    validate.add_argument("--directory", default=".org-memory/items")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = MarkdownMemoryRepository(args.directory)
    count, errors = repository.validate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"valid: {count} memories")
    return 0
