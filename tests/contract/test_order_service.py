from sample_app.application.orders import OrderNotFoundError, OrderService
from sample_app.domain.order import Order


class InMemoryOrders:
    def __init__(self) -> None:
        self.orders: dict[str, Order] = {}

    def add(self, order: Order) -> None:
        self.orders[order.order_id] = order

    def get(self, order_id: str) -> Order | None:
        return self.orders.get(order_id)

    def list(self) -> list[Order]:
        return sorted(self.orders.values(), key=lambda order: order.order_id)


def test_service_uses_repository_for_create_get_and_list() -> None:
    service = OrderService(InMemoryOrders())

    created = service.create("order-2", "cable", 3)
    service.create("order-1", "adapter", 1)

    assert service.get("order-2") == created
    assert [order.order_id for order in service.list()] == ["order-1", "order-2"]


def test_service_reports_missing_order() -> None:
    service = OrderService(InMemoryOrders())

    try:
        service.get("missing")
    except OrderNotFoundError as error:
        assert str(error) == "order not found: missing"
    else:
        raise AssertionError("missing order was accepted")
