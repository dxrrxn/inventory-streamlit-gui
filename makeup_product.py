from brand import Brand
from product import Product, DEFAULT_PAR_LEVEL


class MakeupProduct(Product):
    """Makeup, e.g. foundation, lipstick and eyeshadow. Extra detail: shade."""

    CATEGORY = "makeup"
    CATEGORY_NAME = "Makeup"

    def __init__(self, product_id: str, name: str, price: float, stock: int, brand: Brand,
                 shade: str = "", par_level: int = DEFAULT_PAR_LEVEL):
        super().__init__(product_id, name, price, stock, brand, par_level)
        shade = str(shade).strip()
        if not shade:
            raise ValueError("Shade cannot be empty.")
        self.__shade: str = shade

    def get_detail_label(self) -> str:
        return "Shade"

    def get_detail(self) -> str:
        return self.__shade

    def get_care_tip(self) -> str:
        return f"Shade {self.__shade}: swatch the tester to match it with the customer."
