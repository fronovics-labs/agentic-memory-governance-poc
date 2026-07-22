"""Order domain model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    item: str
    quantity: int

    def __post_init__(self) -> None:
        if not isinstance(self.order_id, str) or not self.order_id.strip():
            raise ValueError("order_id must not be empty")
        if not isinstance(self.item, str) or not self.item.strip():
            raise ValueError("item must not be empty")
        if (
            not isinstance(self.quantity, int)
            or isinstance(self.quantity, bool)
            or self.quantity < 1
        ):
            raise ValueError("quantity must be a positive integer")
