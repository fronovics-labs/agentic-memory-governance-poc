"""Top-level lab command; feature commands are added by their owning tasks."""

import sys
from argparse import ArgumentParser
from collections.abc import Sequence

from lab.memory.renderer import render_context
from lab.memory.repository import MarkdownMemoryRepository
from lab.memory.retrieval import search_memories


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="lab", description="Agent memory governance laboratory")
    commands = parser.add_subparsers(dest="command", required=True)
    memory = commands.add_parser("memory")
    memory_commands = memory.add_subparsers(dest="memory_command", required=True)
    validate = memory_commands.add_parser("validate")
    validate.add_argument("--directory", default=".org-memory/items")
    search = memory_commands.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--directory", default=".org-memory/items")
    context = memory_commands.add_parser("context")
    context.add_argument("--prompt", required=True)
    context.add_argument("--path")
    context.add_argument("--directory", default=".org-memory/items")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = MarkdownMemoryRepository(args.directory)
    if args.memory_command == "validate":
        count, errors = repository.validate()
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"valid: {count} memories")
        return 0

    query = args.query if args.memory_command == "search" else args.prompt
    path = None if args.memory_command == "search" else args.path
    try:
        rendered = render_context(search_memories(repository, query, path=path))
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    if rendered:
        print(rendered)
    return 0
