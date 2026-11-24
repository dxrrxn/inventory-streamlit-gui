from brand import Brand
from product import Product


class HairProduct(Product):
    """Hair, e.g. shampoo, conditioner and styling. Extra detail: hair type."""

    CATEGORY = "hair"
    CATEGORY_NAME = "Hair"
    HAIR_TYPES = ("All", "Straight", "Wavy", "Curly", "Coily")

    def __init__(self, product_id: str, name: str, price: float, stock: int, brand: Brand,
                 hair_type: str = "All"):
        super().__init__(product_id, name, price, stock, brand)
        hair_type = str(hair_type).strip().capitalize()
        if hair_type not in self.HAIR_TYPES:
            raise ValueError(f"Hair type must be one of: {', '.join(self.HAIR_TYPES)}.")
        self.__hair_type: str = hair_type

    def get_detail_label(self) -> str:
        return "Hair type"

    def get_detail(self) -> str:
        return self.__hair_type

    def get_care_tip(self) -> str:
        if self.__hair_type == "All":
            return "Suits all hair types."
        return f"Made for {self.__hair_type.lower()} hair."
