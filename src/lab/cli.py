"""Top-level lab command; feature commands are added by their owning tasks."""

import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from lab.memory.renderer import render_context
from lab.memory.repository import MarkdownMemoryRepository
from lab.memory.retrieval import search_memories
from lab.runs.baseline import default_runs_root, freeze_baseline, repository_root, verify_baseline
from lab.runs.workspace import archive_run, create_run, reset_run, verify_run


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
    context.add_argument("--path", required=True)
    context.add_argument("--directory", default=".org-memory/items")

    baseline = commands.add_parser("baseline")
    baseline_commands = baseline.add_subparsers(dest="baseline_command", required=True)
    for command in ("freeze", "verify"):
        baseline_command = baseline_commands.add_parser(command)
        baseline_command.add_argument("--name", required=True)

    run = commands.add_parser("run")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    create = run_commands.add_parser("create")
    create.add_argument("--id", required=True)
    create.add_argument("--mode", choices=("audit", "block"), required=True)
    for command in ("reset", "verify", "archive"):
        run_command = run_commands.add_parser(command)
        run_command.add_argument("--id", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in ("baseline", "run"):
        try:
            root = repository_root()
            runs_root = default_runs_root(root)
            if args.command == "baseline":
                if args.baseline_command == "freeze":
                    created = freeze_baseline(root, runs_root, args.name)
                    print(created)
                else:
                    verify_baseline(root, runs_root, args.name)
                    print(f"verified baseline: {args.name}")
                return 0

            run_id = args.id
            if args.run_command == "create":
                created = create_run(root, runs_root, run_id, args.mode)
                print(created)
            elif args.run_command == "reset":
                print(reset_run(root, runs_root, run_id))
            elif args.run_command == "verify":
                verify_run(root, runs_root, run_id)
                print(f"verified run: {run_id}")
            else:
                print(archive_run(root, runs_root, run_id))
            return 0
        except (OSError, ValueError) as caught:
            print(caught, file=sys.stderr)
            return 1

    repository = MarkdownMemoryRepository(args.directory)
    if args.memory_command == "validate":
        count, errors = repository.validate()
        if errors:
            for validation_error in errors:
                print(validation_error, file=sys.stderr)
            return 1
        print(f"valid: {count} memories")
        return 0

    query = args.query if args.memory_command == "search" else args.prompt
    path = None if args.memory_command == "search" else args.path
    try:
        rendered = render_context(search_memories(repository, query, path=path))
    except (OSError, ValueError) as caught:
        print(caught, file=sys.stderr)
        return 1
    if rendered:
        print(rendered)
    return 0
