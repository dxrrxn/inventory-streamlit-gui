"""Tests for exception handling (Section 5)."""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from main import get_positive_float
from supplier import Supplier
from inventory import Inventory
from file_handler import load_products

PRODUCTS_CSV = """product_type,product_id,name,price,stock_quantity
physical,P001,Desk Lamp,25.00,10
digital,D001,Photo Editor,49.90,100
service,S001,Installation,30.00,5
physical,P002,Office Chair,abc,3
physical,P003,Monitor Stand,39.50,7
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
        self.supplier = Supplier("S001", "Music World", "sales@musicworld.com")
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
            load_products(path, inventory, self.supplier)
        return inventory, output.getvalue().splitlines()

    def test_bad_rows_skipped_and_good_rows_load(self):
        inventory, lines = self.run_load(self.path)
        ids = [p.get_product_id() for p in inventory.get_products()]
        self.assertEqual(ids, ["P001", "D001", "P003"])
        self.assertEqual(lines, [
            "Row 4 skipped: Unknown product type: service",
            "Row 5 skipped: could not convert string to float: 'abc'",
            "3 products loaded.",
            "Load attempt finished.",
        ])

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