from brand import Brand
from body_product import BodyProduct
from face_product import FaceProduct
from hair_product import HairProduct
from makeup_product import MakeupProduct
from product import Product


class ProductFactory:
    """Factory pattern: the one place that decides which Product class to create.

    The rest of the program asks the factory for a Product and never needs to
    know about the category classes. A new category is one more entry in CATEGORIES.
    """

    CATEGORIES: dict[str, type[Product]] = {
        "face": FaceProduct,
        "makeup": MakeupProduct,
        "hair": HairProduct,
        "body": BodyProduct,
    }

    @classmethod
    def create(cls, category: str, product_id: str, name: str, price: float,
               stock_quantity: int, brand: Brand, detail="") -> Product:
        """detail is the category's extra value: skin type, shade, hair type or size in ml."""
        product_class = cls.CATEGORIES.get(str(category).strip().lower())
        if product_class is None:
            raise ValueError(f"Unknown category: {category}")
        return product_class(product_id, name, price, stock_quantity, brand, detail)

    @classmethod
    def from_dict(cls, data: dict, brands: dict[str, Brand]) -> Product:
        """Rebuild a product saved with to_dict() (from JSON or MongoDB).

        Products of the same brand share one Brand object: `brands` remembers them by name.
        Raises KeyError, TypeError or ValueError if the record is damaged.
        """
        brand_data = data["brand"]
        key = str(brand_data["name"]).strip().lower()
        if key not in brands:
            brands[key] = Brand(brand_data["name"], brand_data.get("country", ""))
        return cls.create(data["category"], data["id"], data["name"], data["price"],
                          data["stock"], brands[key], data.get("detail", ""))
