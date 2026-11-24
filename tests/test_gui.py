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
            InventoryGui(ui, self.path).run()
            rerun = False
        except RerunRequested:
            rerun = True
        return ui, rerun

    def inventory(self):
        return self.state["inventory"]


class TestProductsPage(GuiTestCase):

    def test_loads_inventory_json_and_lists_every_product(self):
        ui, _ = self.show("Products")
        self.assertIn("inventory.json found.\nInventory loaded successfully.", ui.texts("info")[0])
        rows = ui.texts("dataframe")[0]
        self.assertEqual([row["ID"] for row in rows], ["P001", "D001", "P003", "P010"])
        guitar = rows[3]
        self.assertEqual(guitar["Type"], "Physical")
        self.assertEqual(guitar["Shipping"], "$12.00")          # 5 + 2 x 3.5 kg
        self.assertEqual(rows[1]["Shipping"], "-")              # digital: not CanBeShipped


class TestAddProduct(GuiTestCase):

    def test_adds_a_digital_product_with_an_existing_supplier(self):
        _, rerun = self.show("Add product", {"add_type": "digital", "add_id": "D002", "add_name": "Antivirus",
                                             "add_price": 59.0, "add_stock": 20, "add_size": 300.0},
                             clicks={"add_button"})
        self.assertTrue(rerun)
        product = self.inventory().find_product("d002")
        self.assertEqual(product.get_download_size(), 300.0)
        # The supplier object is shared with the other products, not copied.
        self.assertIs(product.get_supplier(), self.inventory().find_product("P001").get_supplier())
        self.assertTrue(self.state["unsaved"])

    def test_rejects_duplicate_id_and_missing_fields(self):
        ui, _ = self.show("Add product", {"add_id": "p001", "add_name": "Lamp"}, clicks={"add_button"})
        self.assertIn("A product with this ID already exists.", ui.texts("error"))
        ui, _ = self.show("Add product", {"add_id": "P099", "add_name": ""}, clicks={"add_button"})
        self.assertIn("Product ID and name cannot be empty.", ui.texts("error"))

    def test_new_supplier_needs_all_fields(self):
        inputs = {"add_id": "P099", "add_name": "Drum", "add_supplier": "+ New supplier", "add_sid": "S002"}
        ui, _ = self.show("Add product", inputs, clicks={"add_button"})
        self.assertIn("Fill in the supplier ID, name and email.", ui.texts("error"))
        inputs.update({"add_sname": "Drum Shop", "add_semail": "hi@drums.com"})
        self.show("Add product", inputs, clicks={"add_button"})
        self.assertEqual(self.inventory().find_product("P099").get_supplier().get_name(), "Drum Shop")


class TestStockAndRemove(GuiTestCase):

    def test_update_stock(self):
        self.show("Update stock", {"stock_product": "P003", "stock_P003": 42}, clicks={"stock_button"})
        self.assertEqual(self.inventory().find_product("P003").get_stock(), 42)

    def test_remove_needs_the_tick_box(self):
        self.show("Remove product", {"remove_product": "P003"}, clicks={"remove_button"})
        self.assertIsNotNone(self.inventory().find_product("P003"))
        self.show("Remove product", {"remove_product": "P003", "remove_sure_P003": True}, clicks={"remove_button"})
        self.assertIsNone(self.inventory().find_product("P003"))


class TestSearch(GuiTestCase):

    def test_physical_product_shows_shipping_and_digital_shows_download_size(self):
        ui, _ = self.show("Search product", {"search_id": "p010"})
        details = dict((row["Detail"], row["Value"]) for row in ui.texts("dataframe")[0])
        self.assertEqual(details["Shipping cost"], "$12.00")
        ui, _ = self.show("Search product", {"search_id": "D001"})
        details = dict((row["Detail"], row["Value"]) for row in ui.texts("dataframe")[0])
        self.assertIn("Download size", details)
        self.assertNotIn("Shipping cost", details)

    def test_unknown_id(self):
        ui, _ = self.show("Search product", {"search_id": "X999"})
        self.assertIn("Product not found.", ui.texts("warning"))


class TestOrder(GuiTestCase):

    def test_builds_an_order_and_applies_the_chosen_discount(self):
        self.show("Create order", {"order_product": "P010", "order_qty": 1}, clicks={"order_add"})
        ui, _ = self.show("Create order", {"order_product": "P001", "order_qty": 2,
                                           "order_discount": "$20 off orders of $200 or more"},
                          clicks={"order_add"})
        metrics = dict(ui.texts("metric"))
        self.assertEqual(metrics["Subtotal"], "$400.00")       # 350 + 2 x 25
        self.assertEqual(metrics["Discount"], "BulkDiscount")
        self.assertEqual(metrics["Total"], "$380.00")
        self.assertFalse(self.state["unsaved"])                # an order doesn't change the inventory


class TestImportAndSave(GuiTestCase):

    def test_import_reports_bad_rows_and_loads_good_ones(self):
        csv_text = (b"product_type,product_id,name,price,stock_quantity\n"
                    b"physical,P050,Speaker,80,4\nservice,S001,Repair,30,1\n")
        upload = SimpleNamespace(getvalue=lambda: csv_text)
        self.show("Import from CSV", {"csv_file": upload}, clicks={"csv_button"})
        ui, _ = self.show("Products")
        message = ui.texts("info")[0]
        self.assertIn("Row 3 skipped: Unknown product type: service", message)
        self.assertIn("1 products loaded.", message)
        self.assertIsNotNone(self.inventory().find_product("P050"))

    def test_save_writes_the_json_file(self):
        self.show("Update stock", {"stock_product": "P001", "stock_P001": 3}, clicks={"stock_button"})
        self.assertTrue(self.state["unsaved"])
        self.show("Products", clicks={"save"})
        self.assertFalse(self.state["unsaved"])
        with open(self.path) as file:
            saved = {item["id"]: item for item in json.load(file)}
        self.assertEqual(saved["P001"]["stock"], 3)


if __name__ == "__main__":
    unittest.main()
