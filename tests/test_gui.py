"""Tests for the inventory pages of the Streamlit GUI, using a fake Streamlit (no browser).

Each test logs in as amy, who works at the Kovan store. Kovan has no saved file yet,
so it starts from a temporary copy of the sample inventory.json.
"""
import json
import os
from types import SimpleNamespace

from app_test_case import AppTestCase


class GuiTestCase(AppTestCase):

    def setUp(self):
        super().setUp()
        self.add_accounts()
        self.log_in("amy")


class TestProductsPage(GuiTestCase):

    def test_lists_every_product_with_its_category_detail(self):
        ui, _ = self.show("Products")
        self.assertIn("inventory.json found.\nInventory loaded successfully.", ui.texts("info")[0])
        rows = {row["ID"]: row for row in ui.texts("dataframe")[0]}
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows["M001"]["Detail"], "Shade: 240")
        self.assertEqual(rows["B002"]["Detail"], "Size (ml): 100")
        self.assertEqual(rows["F002"]["Status"], "Below PAR: order 4")     # stock 4, PAR 8
        self.assertEqual(rows["F001"]["Status"], "OK")

    def test_filters_by_category_brand_and_below_par(self):
        ui, _ = self.show("Products", {"filter_category": ["body"]})
        self.assertEqual([r["ID"] for r in ui.texts("dataframe")[0]], ["B001", "B002", "B003"])
        ui, _ = self.show("Products", {"filter_brand": ["Dior"]})
        self.assertEqual([r["ID"] for r in ui.texts("dataframe")[0]], ["M003", "B002"])
        ui, _ = self.show("Products", {"filter_below_par": True})
        self.assertEqual([r["ID"] for r in ui.texts("dataframe")[0]],
                         ["F002", "F003", "M002", "M003", "H002", "B002", "B003"])
        self.assertIn(("Below PAR", 7), ui.texts("metric"))


class TestAddProduct(GuiTestCase):

    def test_adds_a_makeup_product_with_an_existing_brand(self):
        _, rerun = self.show("Add product", {"add_category": "makeup", "add_id": "M010",
                                             "add_name": "Gloss Bomb", "add_brand": "Fenty Beauty",
                                             "add_price": 30.0, "add_stock": 20, "add_par": 25,
                                             "add_shade": "Fenty Glow"},
                             clicks={"add_button"})
        self.assertTrue(rerun)
        product = self.inventory().find_product("m010")
        self.assertEqual(product.get_detail(), "Fenty Glow")
        self.assertEqual(product.get_par_level(), 25)
        self.assertTrue(product.is_below_par())
        # The brand object is shared with Fenty's other products, not copied.
        self.assertIs(product.get_brand(), self.inventory().find_product("M001").get_brand())
        self.assertEqual(self.state["unsaved"], {"Kovan"})

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

    def test_update_stock_and_par(self):
        self.show("Update stock & PAR", {**self.pick("stock", "B003"), "stock_B003": 4, "par_B003": 12},
                  clicks={"stock_button"})
        product = self.inventory().find_product("B003")
        self.assertEqual((product.get_stock(), product.get_par_level()), (4, 12))
        self.assertIn("Still below PAR: order 8.", self.state["flash"])

    def test_remove_needs_the_tick_box(self):
        self.show("Remove product", {**self.pick("remove", "H002")}, clicks={"remove_button"})
        self.assertIsNotNone(self.inventory().find_product("H002"))
        self.show("Remove product", {**self.pick("remove", "H002"), "remove_sure_H002": True},
                  clicks={"remove_button"})
        self.assertIsNone(self.inventory().find_product("H002"))


class TestSearch(GuiTestCase):

    def test_pick_category_then_brand_then_product(self):
        ui, _ = self.show("Search product", self.pick("search", "F002"))
        details = {row["Detail"]: row["Value"] for row in ui.texts("dataframe")[0]}
        self.assertEqual(details["ID"], "F002")
        self.assertEqual(details["Skin type"], "Dry")
        self.assertEqual(details["Brand"], "Drunk Elephant (USA)")
        self.assertEqual(details["Stock"], "4 (PAR 8)")
        self.assertEqual(details["Restock"], "Below PAR: order 4")
        self.assertIn("dry skin", details["Tip"])

    def test_lists_only_offer_what_matches_the_earlier_choice(self):
        ui, _ = self.show("Search product", {"search_category": "body", "search_brand_body": "Dior"})
        details = {row["Detail"]: row["Value"] for row in ui.texts("dataframe")[0]}
        self.assertEqual(details["ID"], "B002")                 # Dior's only body product
        ui, _ = self.show("Search product", {"search_category": "hair"})
        details = {row["Detail"]: row["Value"] for row in ui.texts("dataframe")[0]}
        self.assertEqual(details["Brand"], "Olaplex (USA)")     # brands are listed A-Z: Olaplex, OUAI

    def test_text_search_is_still_there(self):
        ui, _ = self.show("Search product", {"search_text": "dior"})
        self.assertEqual([r["ID"] for r in ui.texts("dataframe")[1]], ["M003", "B002"])
        ui, _ = self.show("Search product", {"search_text": "X999"})
        self.assertIn("Product not found.", ui.texts("warning"))


class TestRestockList(GuiTestCase):

    def test_lists_products_below_par_grouped_by_brand(self):
        ui, _ = self.show("Restock list")
        metrics = dict(ui.texts("metric"))
        self.assertEqual(metrics["Products to restock"], 7)
        self.assertEqual(metrics["Units to order"], 24)          # 4+1+7+1+5+2+4
        brands = [text.split("**")[1] for text in ui.texts("markdown")]
        self.assertEqual(brands, ["Dior", "Drunk Elephant", "OUAI", "Rare Beauty", "Sol de Janeiro"])
        dior = ui.texts("dataframe")[0]
        self.assertEqual([(r["ID"], r["Stock"], r["PAR"], r["Order"]) for r in dior],
                         [("B002", 6, 8, 2), ("M003", 11, 12, 1)])
        file_name, csv_text = ui.texts("download")[0]
        self.assertEqual(file_name, "restock_kovan.csv")
        self.assertIn("Kovan,Rare Beauty,M002,Soft Pinch Liquid Blush,Makeup,Joy,3,10,7", csv_text)

    def test_mark_as_restocked_needs_the_tick_box(self):
        self.show("Restock list", clicks={"restock_button"})
        self.assertEqual(len(self.inventory().get_products_below_par()), 7)
        self.show("Restock list", {"restock_sure": True}, clicks={"restock_button"})
        self.assertEqual(self.inventory().get_products_below_par(), [])
        self.assertEqual(self.inventory().find_product("M002").get_stock(), 10)
        ui, _ = self.show("Restock list")
        self.assertIn("Every product is at or above PAR. Nothing to restock.", ui.texts("success"))


class TestOrder(GuiTestCase):

    def test_builds_an_order_and_applies_the_chosen_discount(self):
        self.show("Create order", {**self.pick("order", "B002"), "order_qty": 1}, clicks={"order_add"})
        ui, _ = self.show("Create order", {**self.pick("order", "M001"), "order_qty": 2,
                                           "order_discount": "$20 off orders of $200 or more"},
                          clicks={"order_add"})
        metrics = dict(ui.texts("metric"))
        self.assertEqual(metrics["Subtotal"], "$331.00")       # 215 + 2 x 58
        self.assertEqual(metrics["Discount"], "BulkDiscount")
        self.assertEqual(metrics["Total"], "$311.00")
        lines = ui.texts("dataframe")[0]
        self.assertEqual([(line["Brand"], line["Name"], line["Qty"]) for line in lines],
                         [("Dior", "Miss Dior Eau de Parfum", 1),
                          ("Fenty Beauty", "Pro Filt'r Soft Matte Foundation", 2)])
        self.assertEqual(self.state["unsaved"], set())          # an order doesn't change the inventory


    def test_confirm_takes_the_order_off_the_stock(self):
        self.show("Create order", {**self.pick("order", "M002"), "order_qty": 2}, clicks={"order_add"})
        _, rerun = self.show("Create order", clicks={"order_confirm"})
        self.assertTrue(rerun)
        self.assertEqual(self.inventory().find_product("M002").get_stock(), 1)          # 3 - 2
        self.assertEqual(self.state["order_lines"]["Kovan"], [])                       # order cleared
        self.assertEqual(self.state["unsaved"], {"Kovan"})                             # needs saving
        self.assertIn("Order O001 confirmed: 2 item(s) taken off the stock.", self.state["flash"])
        self.assertIn("Now below PAR (on the restock list): Soft Pinch Liquid Blush.", self.state["flash"])

    def test_confirm_is_blocked_when_stock_is_short(self):
        self.show("Create order", {**self.pick("order", "B003"), "order_qty": 5}, clicks={"order_add"})
        ui, rerun = self.show("Create order", clicks={"order_confirm"})
        self.assertFalse(rerun)                                                         # button disabled
        self.assertIn("Only 2 Bum Bum Body Firmeza Oil left, but the order needs 5.", ui.texts("warning"))
        self.assertEqual(self.inventory().find_product("B003").get_stock(), 2)


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
        self.show("Update stock & PAR", {**self.pick("stock", "F001"), "stock_F001": 3}, clicks={"stock_button"})
        self.assertEqual(self.state["unsaved"], {"Kovan"})
        self.show("Products", clicks={"save"})
        self.assertEqual(self.state["unsaved"], set())
        with open(os.path.join(self.folder, "stores", "kovan.json")) as file:
            saved = {item["id"]: item for item in json.load(file)}
        self.assertEqual(saved["F001"]["stock"], 3)
        self.assertEqual(saved["F001"]["par"], 15)
        self.assertEqual(saved["F001"]["brand"], {"name": "Laneige", "country": "South Korea"})


if __name__ == "__main__":
    import unittest
    unittest.main()
