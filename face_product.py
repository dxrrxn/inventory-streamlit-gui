from brand import Brand
from product import Product, DEFAULT_PAR_LEVEL


class FaceProduct(Product):
    """Face & skincare, e.g. cleansers, moisturisers and serums. Extra detail: skin type."""

    CATEGORY = "face"
    CATEGORY_NAME = "Face & skincare"
    SKIN_TYPES = ("All", "Normal", "Dry", "Oily", "Combination", "Sensitive")

    def __init__(self, product_id: str, name: str, price: float, stock: int, brand: Brand,
                 skin_type: str = "All", par_level: int = DEFAULT_PAR_LEVEL):
        super().__init__(product_id, name, price, stock, brand, par_level)
        skin_type = str(skin_type).strip().capitalize()
        if skin_type not in self.SKIN_TYPES:
            raise ValueError(f"Skin type must be one of: {', '.join(self.SKIN_TYPES)}.")
        self.__skin_type: str = skin_type

    def get_detail_label(self) -> str:
        return "Skin type"

    def get_detail(self) -> str:
        return self.__skin_type

    def get_care_tip(self) -> str:
        if self.__skin_type == "All":
            return "Suits all skin types."
        return f"Recommend for {self.__skin_type.lower()} skin; offer a patch test first."
