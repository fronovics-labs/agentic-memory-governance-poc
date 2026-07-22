"""Top-level lab command; feature commands are added by their owning tasks."""

from argparse import ArgumentParser
from collections.abc import Sequence


def build_parser() -> ArgumentParser:
    return ArgumentParser(prog="lab", description="Agent memory governance laboratory")


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0
