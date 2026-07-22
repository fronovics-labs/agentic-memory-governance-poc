"""Order use cases and persistence port."""

from typing import Protocol

from sample_app.domain.order import Order


class OrderRepository(Protocol):
    def add(self, order: Order) -> None: ...

    def get(self, order_id: str) -> Order | None: ...

    def list(self) -> list[Order]: ...


class OrderNotFoundError(LookupError):
    pass


class OrderAlreadyExistsError(ValueError):
    pass


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def create(self, order_id: str, item: str, quantity: int) -> Order:
        order = Order(order_id=order_id, item=item, quantity=quantity)
        self._repository.add(order)
        return order

    def get(self, order_id: str) -> Order:
        order = self._repository.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"order not found: {order_id}")
        return order

    def list(self) -> list[Order]:
        return self._repository.list()
