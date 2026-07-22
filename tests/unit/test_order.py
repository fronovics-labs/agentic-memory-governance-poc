import pytest

from sample_app.domain.order import Order


def test_order_accepts_valid_values() -> None:
    assert Order("order-1", "widget", 2).quantity == 2


@pytest.mark.parametrize(
    ("order_id", "item", "quantity", "message"),
    [
        ("", "widget", 1, "order_id"),
        ("order-1", " ", 1, "item"),
        ("order-1", "widget", 0, "quantity"),
    ],
)
def test_order_rejects_invalid_values(
    order_id: str, item: str, quantity: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        Order(order_id, item, quantity)
