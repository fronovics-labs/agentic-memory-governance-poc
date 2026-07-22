"""SQLite order repository."""

import sqlite3
from pathlib import Path

from sample_app.application.orders import OrderAlreadyExistsError
from sample_app.domain.order import Order


class SQLiteOrderRepository:
    def __init__(self, database: str | Path) -> None:
        self._database = database
        with sqlite3.connect(self._database) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    item TEXT NOT NULL,
                    quantity INTEGER NOT NULL
                )
                """
            )

    def add(self, order: Order) -> None:
        try:
            with sqlite3.connect(self._database) as connection:
                connection.execute(
                    "INSERT INTO orders (order_id, item, quantity) VALUES (?, ?, ?)",
                    (order.order_id, order.item, order.quantity),
                )
        except sqlite3.IntegrityError as error:
            raise OrderAlreadyExistsError(f"order already exists: {order.order_id}") from error

    def get(self, order_id: str) -> Order | None:
        with sqlite3.connect(self._database) as connection:
            row = connection.execute(
                "SELECT order_id, item, quantity FROM orders WHERE order_id = ?",
                (order_id,),
            ).fetchone()
        return None if row is None else Order(*row)

    def list(self) -> list[Order]:
        with sqlite3.connect(self._database) as connection:
            rows = connection.execute(
                "SELECT order_id, item, quantity FROM orders ORDER BY order_id"
            ).fetchall()
        return [Order(*row) for row in rows]
