from abc import ABC, abstractmethod

from brand import Brand

LOW_STOCK_LEVEL = 5        # at or below this, a product needs restocking


class Product(ABC):
    """Abstract base class for every Sephora product (SRP: one product only).

    A plain Product can't be created; use FaceProduct, MakeupProduct, HairProduct
    or BodyProduct. Each category adds its own detail (skin type, shade, ...).
    """

    CATEGORY = ""              # set by each subclass, e.g. "face"
    CATEGORY_NAME = ""         # shown on screen, e.g. "Face & skincare"

    def __init__(self, product_id: str, name: str, price: float, stock: int, brand: Brand):
        product_id, name = str(product_id).strip(), str(name).strip()
        if not product_id or not name:
            raise ValueError("Product ID and name cannot be empty.")
        price = float(price)                      # raises ValueError if it isn't a number
        if price <= 0:
            raise ValueError("Price must be greater than zero.")
        self.__product_id: str = product_id
        self.__name: str = name
        self.__price: float = price
        self.__stock: int = 0
        self.__brand: Brand = brand               # association: a reference, not ownership
        self.update_stock(stock)

    # ---------- Read-only access to attributes ----------

    def get_product_id(self) -> str:
        return self.__product_id

    def get_name(self) -> str:
        return self.__name

    def get_price(self) -> float:
        return self.__price

    def get_stock(self) -> int:
        return self.__stock

    def get_brand(self) -> Brand:
        return self.__brand

    # ---------- Behaviour ----------

    def update_stock(self, quantity: int) -> None:
        """Set the stock level. Any whole number from 0 upwards."""
        quantity = int(quantity)
        if quantity < 0:
            raise ValueError("Stock cannot be negative.")
        self.__stock = quantity

    def get_detail_text(self) -> str:
        """The detail as text: whole-number sizes without ".0", e.g. "100" not "100.0"."""
        detail = self.get_detail()
        return f"{detail:g}" if isinstance(detail, float) else str(detail)

    def is_low_stock(self) -> bool:
        return self.__stock <= LOW_STOCK_LEVEL

    def display_information(self) -> None:
        print(f"ID: {self.__product_id} | {self.__brand.get_name()} {self.__name} | "
              f"{self.CATEGORY_NAME} | Price: ${self.__price:.2f} | Stock: {self.__stock} | "
              f"{self.get_detail_label()}: {self.get_detail_text()}")

    def to_dict(self) -> dict:
        """Return the product's data as a dictionary (used when saving to JSON or MongoDB)."""
        return {
            "id": self.__product_id,
            "category": self.CATEGORY,
            "name": self.__name,
            "price": self.__price,
            "stock": self.__stock,
            "brand": self.__brand.to_dict(),
            "detail": self.get_detail(),
        }

    @abstractmethod
    def get_detail_label(self) -> str:
        """The name of this category's extra detail, e.g. "Skin type"."""

    @abstractmethod
    def get_detail(self):
        """This product's value for that detail, e.g. "Oily"."""

    @abstractmethod
    def get_care_tip(self) -> str:
        """A short tip shown to staff when they look the product up."""
