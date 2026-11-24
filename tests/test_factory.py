"""Tests for the Factory pattern (Section 3)."""
import inspect
import unittest

import main
import file_handler
from supplier import Supplier
from product import Product
from physical_product import PhysicalProduct
from digital_product import DigitalProduct
from product_factory import ProductFactory


class TestProductFactory(unittest.TestCase):

    def setUp(self):
        self.supplier = Supplier("S001", "Music World", "sales@musicworld.com")

    def test_creates_physical_product(self):
        product = ProductFactory.create("physical", "P001", "Guitar", 350, 5, self.supplier, weight=3.5)
        self.assertIsInstance(product, PhysicalProduct)
        self.assertIsInstance(product, Product)
        self.assertEqual(product.get_weight(), 3.5)

    def test_creates_digital_product(self):
        product = ProductFactory.create("digital", "D001", "Windows 11", 199, 100,
                                        self.supplier, download_size=5400)
        self.assertIsInstance(product, DigitalProduct)
        self.assertEqual(product.get_download_size(), 5400)

    def test_type_is_not_case_sensitive(self):
        product = ProductFactory.create(" Physical ", "P001", "Guitar", 350, 5, self.supplier)
        self.assertIsInstance(product, PhysicalProduct)

    def test_unknown_type_raises_clear_value_error(self):
        with self.assertRaises(ValueError) as context:
            ProductFactory.create("service", "S001", "Installation", 30, 5, self.supplier)
        self.assertEqual(str(context.exception), "Unknown product type: service")

    def test_main_and_file_handler_use_the_factory(self):
        for module in (main, file_handler):
            source = inspect.getsource(module)
            self.assertIn("ProductFactory.create(", source)
            self.assertNotIn("PhysicalProduct(", source)
            self.assertNotIn("DigitalProduct(", source)


if __name__ == "__main__":
    unittest.main()