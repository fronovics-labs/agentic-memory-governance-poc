"""CLI composition root for the synthetic order application."""

import json
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from dataclasses import asdict

from sample_app.application.orders import OrderNotFoundError, OrderService
from sample_app.infrastructure.sqlite_orders import SQLiteOrderRepository


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="orders", description="SQLite-backed order service")
    parser.add_argument("--database", default="orders.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create")
    create.add_argument("--id", required=True)
    create.add_argument("--item", required=True)
    create.add_argument("--quantity", required=True, type=int)

    get = commands.add_parser("get")
    get.add_argument("--id", required=True)
    commands.add_parser("list")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = OrderService(SQLiteOrderRepository(args.database))

    try:
        if args.command == "create":
            result: object = asdict(service.create(args.id, args.item, args.quantity))
        elif args.command == "get":
            result = asdict(service.get(args.id))
        else:
            result = [asdict(order) for order in service.list()]
    except (OrderNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
