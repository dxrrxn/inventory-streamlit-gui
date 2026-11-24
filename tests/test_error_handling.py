"""Tests for exception handling (Section 5)."""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from main import get_positive_float
from inventory import Inventory
from file_handler import load_products

PRODUCTS_CSV = """category,product_id,name,brand,price,stock_quantity,detail
face,F001,Water Cream,Tatcha,98.00,12,Dry
makeup,M001,Gloss Bomb,Fenty Beauty,30.00,20,Fenty Glow
nails,N001,Nail Polish,Sephora Collection,12.00,30,Red
face,F002,Toner,Glow Recipe,abc,8,Normal
makeup,M002,Concealer,Rare Beauty,32.00,15,
hair,H001,Shampoo,Olaplex,42.00,9,Frizzy
body,B001,Bum Bum Cream,Sol de Janeiro,65.00,3,240
"""

class TestGetPositiveFloat(unittest.TestCase):

    def test_keeps_asking_until_valid(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["abc", "-5", "12.50"]), redirect_stdout(output):
            value = get_positive_float("Price: ")
        self.assertEqual(value, 12.50)
        self.assertEqual(output.getvalue().splitlines(), [
            "Please enter a valid number, e.g. 12.50",
            "Please enter a number greater than zero.",
        ])


class TestLoadProducts(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "products.csv")
        with open(self.path, "w", newline="") as file:
            file.write(PRODUCTS_CSV)

    def tearDown(self):
        self.folder.cleanup()

    def run_load(self, path: str) -> tuple[Inventory, list[str]]:
        inventory = Inventory()
        output = io.StringIO()
        with redirect_stdout(output):
            load_products(path, inventory)
        return inventory, output.getvalue().splitlines()

    def test_bad_rows_skipped_and_good_rows_load(self):
        inventory, lines = self.run_load(self.path)
        ids = [p.get_product_id() for p in inventory.get_products()]
        self.assertEqual(ids, ["F001", "M001", "B001"])
        self.assertEqual(lines, [
            "Row 4 skipped: Unknown category: nails",
            "Row 5 skipped: could not convert string to float: 'abc'",
            "Row 6 skipped: Shade cannot be empty.",
            "Row 7 skipped: Hair type must be one of: All, Straight, Wavy, Curly, Coily.",
            "3 products loaded.",
            "Load attempt finished.",
        ])

    def test_products_of_one_brand_share_a_brand_object(self):
        inventory = Inventory()
        with redirect_stdout(io.StringIO()):
            load_products(self.path, inventory)
            load_products(self.path, inventory)          # second time: every row already exists
        self.assertEqual(len(inventory.get_products()), 3)
        self.assertEqual(sorted(inventory.get_brands()), ["fenty beauty", "sol de janeiro", "tatcha"])

    def test_missing_file_handled_gracefully(self):
        missing = os.path.join(self.folder.name, "missing.csv")
        inventory, lines = self.run_load(missing)
        self.assertEqual(inventory.get_products(), [])
        self.assertEqual(lines, [
            f"Products file not found: {missing}",
            "Load attempt finished.",
        ])


if __name__ == "__main__":
    unittest.main()