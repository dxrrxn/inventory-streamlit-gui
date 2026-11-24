from brand import Brand
from product import Product

TRAVEL_SIZE_ML = 100       # liquids up to 100 ml can go in cabin baggage


class BodyProduct(Product):
    """Body & fragrance, e.g. body wash, lotion and perfume. Extra detail: size in ml."""

    CATEGORY = "body"
    CATEGORY_NAME = "Body & fragrance"

    def __init__(self, product_id: str, name: str, price: float, stock: int, brand: Brand,
                 size_ml: float = 0.0):
        super().__init__(product_id, name, price, stock, brand)
        size_ml = float(size_ml)
        if size_ml <= 0:
            raise ValueError("Size must be greater than 0 ml.")
        self.__size_ml: float = size_ml

    def get_detail_label(self) -> str:
        return "Size (ml)"

    def get_detail(self) -> float:
        return self.__size_ml

    def get_care_tip(self) -> str:
        if self.__size_ml <= TRAVEL_SIZE_ML:
            return f"{self.__size_ml:g} ml: travel size, allowed in cabin baggage."
        return f"{self.__size_ml:g} ml: full size, too big for cabin baggage."
