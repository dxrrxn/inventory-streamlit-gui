"""Tests for the Factory pattern."""
import inspect
import unittest

import main
import file_handler
from brand import Brand
from product import Product
from face_product import FaceProduct
from makeup_product import MakeupProduct
from hair_product import HairProduct
from body_product import BodyProduct
from product_factory import ProductFactory


class TestProductFactory(unittest.TestCase):

    def setUp(self):
        self.brand = Brand("Laneige", "South Korea")

    def test_creates_each_category(self):
        cases = [("face", "Oily", FaceProduct), ("makeup", "Ruby Woo", MakeupProduct),
                 ("hair", "Curly", HairProduct), ("body", 250, BodyProduct)]
        for category, detail, expected in cases:
            product = ProductFactory.create(category, "X1", "Item", 20, 5, self.brand, detail)
            self.assertIsInstance(product, expected)
            self.assertIsInstance(product, Product)
            self.assertEqual(product.CATEGORY, category)

    def test_category_is_not_case_sensitive(self):
        product = ProductFactory.create(" Face ", "F1", "Cream", 30, 5, self.brand, "dry")
        self.assertIsInstance(product, FaceProduct)
        self.assertEqual(product.get_detail(), "Dry")

    def test_unknown_category_raises_clear_value_error(self):
        with self.assertRaises(ValueError) as context:
            ProductFactory.create("nails", "N1", "Polish", 12, 5, self.brand, "Red")
        self.assertEqual(str(context.exception), "Unknown category: nails")

    def test_from_dict_rebuilds_a_saved_product_and_shares_brands(self):
        original = ProductFactory.create("body", "B1", "Mist", 39, 22, self.brand, 90)
        brands = {}
        first = ProductFactory.from_dict(original.to_dict(), brands)
        second = ProductFactory.from_dict(original.to_dict(), brands)
        self.assertIsInstance(first, BodyProduct)
        self.assertEqual(first.to_dict(), original.to_dict())
        self.assertIs(first.get_brand(), second.get_brand())

    def test_main_and_file_handler_use_the_factory(self):
        for module in (main, file_handler):
            source = inspect.getsource(module)
            self.assertIn("ProductFactory.", source)
            for name in ("FaceProduct(", "MakeupProduct(", "HairProduct(", "BodyProduct("):
                self.assertNotIn(name, source)


if __name__ == "__main__":
    unittest.main()
