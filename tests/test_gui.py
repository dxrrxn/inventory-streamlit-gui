"""Tests for the Streamlit GUI, using a fake Streamlit (no browser needed).

Each test copies inventory.json to a temporary folder, so the real file is never changed.
"""
import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace

from fake_streamlit import FakeStreamlit, RerunRequested
from json_inventory_store import JsonInventoryStore
from streamlit_app import InventoryGui, APP_DIR


class GuiTestCase(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "inventory.json")
        shutil.copy(os.path.join(APP_DIR, "inventory.json"), self.path)
        self.state = {}

    def tearDown(self):
        shutil.rmtree(self.folder)

    def show(self, page, inputs=None, clicks=()):
        """Draw one page, like one Streamlit run. Returns the fake and whether it asked to rerun."""
        ui = FakeStreamlit(inputs={"page": page, **(inputs or {})}, clicks=clicks,
                           session_state=self.state)
        try:
            InventoryGui(ui, JsonInventoryStore(self.path)).run()
            rerun = False
        except RerunRequested:
            rerun = True
        return ui, rerun

    def inventory(self):
        return self.state["inventory"]


class TestProductsPage(GuiTestCase):

    def test_lists_every_product_with_its_category_detail(self):
        ui, _ = self.show("Products")
        self.assertIn("inventory.json found.\nInventory loaded successfully.", ui.texts("info")[0])
        rows = {row["ID"]: row for row in ui.texts("dataframe")[0]}
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows["M001"]["Detail"], "Shade: 240")
        self.assertEqual(rows["B002"]["Detail"], "Size (ml): 100")
        self.assertEqual(rows["B003"]["Status"], "Low stock")

    def test_filters_by_category_brand_and_low_stock(self):
        ui, _ = self.show("Products", {"filter_category": ["body"]})
        self.assertEqual([r["ID"] for r in ui.texts("dataframe")[0]], ["B001", "B002", "B003"])
        ui, _ = self.show("Products", {"filter_brand": ["Dior"]})
        self.assertEqual([r["ID"] for r in ui.texts("dataframe")[0]], ["M003", "B002"])
        ui, _ = self.show("Products", {"filter_low": True})
        self.assertEqual([r["ID"] for r in ui.texts("dataframe")[0]], ["F002", "M002", "H002", "B003"])
        self.assertIn(("Low stock", 4), ui.texts("metric"))


class TestAddProduct(GuiTestCase):

    def test_adds_a_makeup_product_with_an_existing_brand(self):
        _, rerun = self.show("Add product", {"add_category": "makeup", "add_id": "M010",
                                             "add_name": "Gloss Bomb", "add_brand": "Fenty Beauty",
                                             "add_price": 30.0, "add_stock": 20, "add_shade": "Fenty Glow"},
                             clicks={"add_button"})
        self.assertTrue(rerun)
        product = self.inventory().find_product("m010")
        self.assertEqual(product.get_detail(), "Fenty Glow")
        # The brand object is shared with Fenty's other products, not copied.
        self.assertIs(product.get_brand(), self.inventory().find_product("M001").get_brand())
        self.assertTrue(self.state["unsaved"])

    def test_new_brand_and_body_size(self):
        self.show("Add product", {"add_category": "body", "add_id": "B010", "add_name": "Body Lotion",
                                  "add_brand": "+ New brand", "add_brand_name": "Glow Recipe",
                                  "add_brand_country": "USA", "add_size": 150.0},
                  clicks={"add_button"})
        product = self.inventory().find_product("B010")
        self.assertEqual(product.get_brand().get_country(), "USA")
        self.assertEqual(product.get_detail(), 150.0)

    def test_errors_are_shown(self):
        ui, _ = self.show("Add product", {"add_id": "f001", "add_name": "Cream"}, clicks={"add_button"})
        self.assertIn("A product with this ID already exists.", ui.texts("error"))
        ui, _ = self.show("Add product", {"add_id": "F099", "add_name": ""}, clicks={"add_button"})
        self.assertIn("Product ID and name cannot be empty.", ui.texts("error"))
        ui, _ = self.show("Add product", {"add_category": "makeup", "add_id": "M099", "add_name": "Kohl",
                                          "add_shade": ""}, clicks={"add_button"})
        self.assertIn("Shade cannot be empty.", ui.texts("error"))
        ui, _ = self.show("Add product", {"add_id": "F099", "add_name": "Cream", "add_brand": "+ New brand"},
                          clicks={"add_button"})
        self.assertIn("Fill in the brand name.", ui.texts("error"))


class TestStockAndRemove(GuiTestCase):

    def test_update_stock(self):
        self.show("Update stock", {"stock_product": "B003", "stock_B003": 42}, clicks={"stock_button"})
        self.assertEqual(self.inventory().find_product("B003").get_stock(), 42)

    def test_remove_needs_the_tick_box(self):
        self.show("Remove product", {"remove_product": "H002"}, clicks={"remove_button"})
        self.assertIsNotNone(self.inventory().find_product("H002"))
        self.show("Remove product", {"remove_product": "H002", "remove_sure_H002": True},
                  clicks={"remove_button"})
        self.assertIsNone(self.inventory().find_product("H002"))


class TestSearch(GuiTestCase):

    def test_by_id_shows_the_category_detail_and_tip(self):
        ui, _ = self.show("Search product", {"search_text": "f002"})
        details = {row["Detail"]: row["Value"] for row in ui.texts("dataframe")[0]}
        self.assertEqual(details["Skin type"], "Dry")
        self.assertEqual(details["Brand"], "Drunk Elephant (USA)")
        self.assertEqual(details["Stock"], "4 (low stock, reorder)")
        self.assertIn("dry skin", details["Tip"])

    def test_by_brand_or_name_lists_matches(self):
        ui, _ = self.show("Search product", {"search_text": "dior"})
        self.assertEqual([r["ID"] for r in ui.texts("dataframe")[0]], ["M003", "B002"])
        ui, _ = self.show("Search product", {"search_text": "X999"})
        self.assertIn("Product not found.", ui.texts("warning"))


class TestOrder(GuiTestCase):

    def test_builds_an_order_and_applies_the_chosen_discount(self):
        self.show("Create order", {"order_product": "B002", "order_qty": 1}, clicks={"order_add"})
        ui, _ = self.show("Create order", {"order_product": "M001", "order_qty": 2,
                                           "order_discount": "$20 off orders of $200 or more"},
                          clicks={"order_add"})
        metrics = dict(ui.texts("metric"))
        self.assertEqual(metrics["Subtotal"], "$331.00")       # 215 + 2 x 58
        self.assertEqual(metrics["Discount"], "BulkDiscount")
        self.assertEqual(metrics["Total"], "$311.00")
        self.assertFalse(self.state["unsaved"])                # an order doesn't change the inventory


class TestImportAndSave(GuiTestCase):

    def test_import_reports_bad_rows_and_loads_good_ones(self):
        csv_text = (b"category,product_id,name,brand,price,stock_quantity,detail\n"
                    b"hair,H050,Dry Shampoo,Dior,40,4,All\nnails,N001,Polish,OPI,15,1,Red\n")
        upload = SimpleNamespace(getvalue=lambda: csv_text)
        self.show("Import from CSV", {"csv_file": upload}, clicks={"csv_button"})
        ui, _ = self.show("Products")
        message = ui.texts("info")[0]
        self.assertIn("Row 3 skipped: Unknown category: nails", message)
        self.assertIn("1 products loaded.", message)
        product = self.inventory().find_product("H050")
        self.assertIs(product.get_brand(), self.inventory().find_product("B002").get_brand())

    def test_save_writes_the_json_file(self):
        self.show("Update stock", {"stock_product": "F001", "stock_F001": 3}, clicks={"stock_button"})
        self.assertTrue(self.state["unsaved"])
        self.show("Products", clicks={"save"})
        self.assertFalse(self.state["unsaved"])
        with open(self.path) as file:
            saved = {item["id"]: item for item in json.load(file)}
        self.assertEqual(saved["F001"]["stock"], 3)
        self.assertEqual(saved["F001"]["brand"], {"name": "Laneige", "country": "South Korea"})


if __name__ == "__main__":
    unittest.main()
