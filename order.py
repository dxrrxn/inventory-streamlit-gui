from product import Product
from order_line import OrderLine
from discount_strategy import DiscountStrategy, NoDiscount


class Order:
    """A customer order made up of OrderLine objects.

    Composition: the Order creates its own OrderLines and manages them.
    Association: the Order uses a DiscountStrategy but does not own it, so
    several orders can share the same strategy object.
    """

    def __init__(self, order_id: str, discount: DiscountStrategy | None = None):
        self.__order_id: str = order_id
        self.__order_lines: list[OrderLine] = []
        self.__discount: DiscountStrategy = discount if discount is not None else NoDiscount()

    def get_order_id(self) -> str:
        return self.__order_id

    def get_discount(self) -> DiscountStrategy:
        return self.__discount

    def set_discount(self, discount: DiscountStrategy) -> None:
        """Swap the discount strategy on an existing order."""
        self.__discount = discount

    def add_order_line(self, product: Product, quantity: int) -> None:
        """Create a new OrderLine inside this Order (it is never created elsewhere)."""
        order_line = OrderLine(product, quantity)
        self.__order_lines.append(order_line)

    def remove_order_line(self, product_id: str) -> bool:
        """Remove the line for this product. Returns False if there is no such line."""
        for order_line in self.__order_lines:
            if order_line.get_product().get_product_id().upper() == product_id.upper():
                self.__order_lines.remove(order_line)
                return True
        return False

    def get_order_lines(self) -> tuple[OrderLine, ...]:
        """Read-only view of the lines, so outside code can't add or move them."""
        return tuple(self.__order_lines)

    def calculate_subtotal(self) -> float:
        """Total of all lines before any discount."""
        return sum(order_line.calculate_subtotal() for order_line in self.__order_lines)

    def calculate_total(self) -> float:
        """Total after discount. The strategy decides the discount, not the Order."""
        return self.__discount.apply(self.calculate_subtotal())

    def get_stock_problems(self) -> list[str]:
        """Products the store doesn't have enough of. A product added on two lines
        counts once, with the quantities added together. [] means the order can go ahead."""
        needed: dict[str, int] = {}
        products: dict[str, Product] = {}
        for order_line in self.__order_lines:
            product = order_line.get_product()
            product_id = product.get_product_id()
            needed[product_id] = needed.get(product_id, 0) + order_line.get_quantity()
            products[product_id] = product
        return [f"Only {products[pid].get_stock()} {products[pid].get_name()} left, "
                f"but the order needs {quantity}."
                for pid, quantity in needed.items() if quantity > products[pid].get_stock()]

    def confirm(self) -> None:
        """The sale goes through: take each line's quantity off its product's stock.
        All or nothing: if any product is short, nothing changes and ValueError explains why."""
        if not self.__order_lines:
            raise ValueError("The order has no items.")
        problems = self.get_stock_problems()
        if problems:
            raise ValueError(" ".join(problems))
        for order_line in self.__order_lines:
            product = order_line.get_product()
            product.update_stock(product.get_stock() - order_line.get_quantity())

    def display_order(self) -> None:
        print(f"Order {self.__order_id}")
        if not self.__order_lines:
            print("(no items)")
        for order_line in self.__order_lines:
            order_line.display_information()
        print(f"Subtotal: ${self.calculate_subtotal():.2f}")
        print(f"Discount: {type(self.__discount).__name__}")
        print(f"Total: ${self.calculate_total():.2f}")