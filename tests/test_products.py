"""Tests for the product classes: abstraction, inheritance, polymorphism,
encapsulation and the Brand association."""
import unittest

from brand import Brand
from product import Product
from face_product import FaceProduct
from makeup_product import MakeupProduct
from hair_product import HairProduct
from body_product import BodyProduct
from inventory import Inventory


class TestProducts(unittest.TestCase):

    def setUp(self):
        self.brand = Brand("Sol de Janeiro", "USA")

    def test_product_is_abstract(self):
        with self.assertRaises(TypeError):
            Product("X1", "Item", 10, 1, self.brand)

    def test_each_category_validates_its_own_detail(self):
        with self.assertRaises(ValueError):
            FaceProduct("F1", "Cream", 30, 5, self.brand, "Shiny")
        with self.assertRaises(ValueError):
            MakeupProduct("M1", "Lipstick", 30, 5, self.brand, "  ")
        with self.assertRaises(ValueError):
            HairProduct("H1", "Shampoo", 30, 5, self.brand, "Frizzy")
        with self.assertRaises(ValueError):
            BodyProduct("B1", "Lotion", 30, 5, self.brand, 0)

    def test_common_rules_come_from_product(self):
        with self.assertRaises(ValueError):
            FaceProduct("F1", "Cream", 0, 5, self.brand, "Dry")         # price must be > 0
        with self.assertRaises(ValueError):
            BodyProduct("B1", "Lotion", 30, -1, self.brand, 100)        # stock can't be negative
        with self.assertRaises(ValueError):
            MakeupProduct("", "Lipstick", 30, 5, self.brand, "999")     # ID can't be empty

    def test_polymorphism_each_category_describes_itself(self):
        products = [FaceProduct("F1", "Cream", 30, 5, self.brand, "Dry"),
                    MakeupProduct("M1", "Lipstick", 30, 5, self.brand, "999"),
                    HairProduct("H1", "Shampoo", 30, 5, self.brand, "Curly"),
                    BodyProduct("B1", "Mist", 30, 5, self.brand, 90)]
        labels = [product.get_detail_label() for product in products]
        self.assertEqual(labels, ["Skin type", "Shade", "Hair type", "Size (ml)"])
        self.assertIn("dry skin", products[0].get_care_tip())
        self.assertIn("travel size", products[3].get_care_tip())
        self.assertIn("full size", BodyProduct("B2", "Perfume", 215, 5, self.brand, 150).get_care_tip())

    def test_detail_text_hides_trailing_zero(self):
        self.assertEqual(BodyProduct("B1", "Mist", 30, 5, self.brand, 90).get_detail_text(), "90")

    def test_low_stock(self):
        product = HairProduct("H1", "Shampoo", 30, 5, self.brand, "All")
        self.assertTrue(product.is_low_stock())
        product.update_stock(6)
        self.assertFalse(product.is_low_stock())

    def test_brand_is_shared_not_owned(self):
        first = BodyProduct("B1", "Mist", 39, 22, self.brand, 90)
        second = BodyProduct("B2", "Cream", 65, 3, self.brand, 240)
        inventory = Inventory()
        inventory.add_product(first)
        inventory.add_product(second)
        self.assertIs(first.get_brand(), second.get_brand())
        self.assertEqual(list(inventory.get_brands()), ["sol de janeiro"])
        inventory.remove_product("B1")
        self.assertEqual(second.get_brand().get_name(), "Sol de Janeiro")   # still exists

    def test_brand_needs_a_name(self):
        with self.assertRaises(ValueError):
            Brand("  ")


if __name__ == "__main__":
    unittest.main()
