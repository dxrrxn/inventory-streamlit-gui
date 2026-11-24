from product import Product
from supplier import Supplier
from physical_product import PhysicalProduct
from digital_product import DigitalProduct


class ProductFactory:
    """Factory pattern: the one place that decides which Product class to create.

    The rest of the program asks the factory for a Product and never needs to
    know about PhysicalProduct or DigitalProduct.
    """

    @staticmethod
    def create(product_type: str, product_id: str, name: str, price: float,
               stock_quantity: int, supplier: Supplier,
               weight: float = 0.0, download_size: float = 0.0) -> Product:
        product_type = product_type.strip().lower()
        if product_type == "physical":
            return PhysicalProduct(product_id, name, price, stock_quantity, supplier, weight)
        elif product_type == "digital":
            return DigitalProduct(product_id, name, price, stock_quantity, supplier, download_size)
        else:
            raise ValueError(f"Unknown product type: {product_type}")