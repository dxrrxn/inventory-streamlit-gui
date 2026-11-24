"""Tests for logging in and which stores each account can open, using a fake Streamlit."""
import json
import os

from app_test_case import AppTestCase, MASTER_PASSWORD, STAFF_PASSWORD
from branch import BRANCH_NAMES


class TestSetupAndLogin(AppTestCase):

    def test_first_run_asks_for_a_master_account(self):
        ui, _ = self.show()
        self.assertIn("First-time setup: create the master account", ui.texts("subheader"))
        ui, _ = self.show(inputs={"setup_password": MASTER_PASSWORD, "setup_confirm": "different"},
                          clicks={"setup_button"})
        self.assertIn("The passwords don't match.", ui.texts("error"))
        _, rerun = self.show(inputs={"setup_password": MASTER_PASSWORD, "setup_confirm": MASTER_PASSWORD},
                             clicks={"setup_button"})
        self.assertTrue(rerun)
        ui, _ = self.show()
        self.assertIn("Staff login", ui.texts("subheader"))           # setup is never shown again

    def test_wrong_and_right_password(self):
        self.add_accounts()
        ui, _ = self.show(inputs={"login_user": "amy", "login_password": "nope-nope"},
                          clicks={"login_button"})
        self.assertIn("Wrong username or password.", ui.texts("error"))
        self.assertNotIn("user", self.state)
        self.show(inputs={"login_user": "amy", "login_password": STAFF_PASSWORD}, clicks={"login_button"})
        self.assertEqual(self.state["user"].get_username(), "amy")

    def test_unreadable_accounts_never_offer_setup(self):
        with open(os.path.join(self.folder, "accounts.json"), "w") as file:
            file.write("{damaged")
        ui, _ = self.show()
        self.assertIn("could not be read", ui.texts("error")[0])
        self.assertNotIn("First-time setup: create the master account", ui.texts("subheader"))

    def test_log_out(self):
        self.add_accounts()
        self.log_in("amy")
        self.show("Update stock & PAR", {**self.pick("stock", "F001"), "stock_F001": 1}, clicks={"stock_button"})
        self.show("Products", clicks={"logout"})
        self.assertNotIn("user", self.state)
        self.assertEqual(self.state["branches"], {})                  # unsaved changes discarded
        ui, _ = self.show()
        self.assertIn("Staff login", ui.texts("subheader"))


class TestStoreAccess(AppTestCase):

    def setUp(self):
        super().setUp()
        self.add_accounts()

    def test_employee_only_sees_their_store(self):
        self.log_in("ben")
        ui, _ = self.show("Products", {"branch": "Kovan"})           # a store they may not pick
        self.assertIn("Punggol", ui.texts("header"))
        self.assertEqual(list(self.state["branches"]), ["Punggol"])

    def test_stores_are_separate(self):
        self.log_in("amy")
        self.show("Update stock & PAR", {**self.pick("stock", "F001"), "stock_F001": 1}, clicks={"stock_button"})
        self.show("Products", clicks={"save"})
        self.log_in("ben")
        self.show("Products")
        self.assertEqual(self.inventory("Kovan").find_product("F001").get_stock(), 1)
        self.assertEqual(self.inventory("Punggol").find_product("F001").get_stock(), 18)
        self.assertTrue(os.path.exists(os.path.join(self.folder, "stores", "kovan.json")))
        self.assertFalse(os.path.exists(os.path.join(self.folder, "stores", "punggol.json")))

    def test_master_overview_of_all_stores(self):
        self.log_in("boss")
        self.state["branches"] = {}
        ui, _ = self.show("Overview", {"branch": "All stores"})
        rows = ui.texts("dataframe")[0]
        self.assertEqual([row["Store"] for row in rows], list(BRANCH_NAMES))
        self.assertEqual(rows[0]["Below PAR"], 7)
        file_name, csv_text = ui.texts("download")[0]
        self.assertEqual(file_name, "restock_all_stores.csv")
        self.assertEqual(csv_text.count("\n"), 1 + 7 * 5)              # header + 7 lines per store

    def test_master_can_open_any_store_and_save_all(self):
        self.log_in("boss")
        self.show("Update stock & PAR", {"branch": "Hougang", **self.pick("stock", "F001"), "stock_F001": 2},
                  clicks={"stock_button"})
        self.show("Update stock & PAR", {"branch": "Serangoon", **self.pick("stock", "F001"), "stock_F001": 3},
                  clicks={"stock_button"})
        self.assertEqual(self.state["unsaved"], {"Hougang", "Serangoon"})
        self.show("Overview", {"branch": "All stores"}, clicks={"save"})
        self.assertEqual(self.state["unsaved"], set())
        self.assertIn("Hougang: Inventory saved to hougang.json.", self.state["flash"])
        with open(os.path.join(self.folder, "stores", "serangoon.json")) as file:
            self.assertEqual(json.load(file)[0]["stock"], 3)

    def test_a_store_fresh_from_its_sample_can_be_saved_straight_away(self):
        self.log_in("amy")
        self.show("Products")                                      # Kovan, no changes made
        self.assertEqual(self.state["unsaved"], set())
        _, rerun = self.show("Products", clicks={"save"})
        self.assertTrue(rerun)
        self.assertTrue(os.path.exists(os.path.join(self.folder, "stores", "kovan.json")))

    def test_master_manages_staff(self):
        self.log_in("boss")
        self.show("Manage staff", {"branch": "All stores", "staff_user": "cara", "staff_store": "Sengkang",
                                   "staff_password": STAFF_PASSWORD}, clicks={"staff_add"})
        ui, _ = self.show("Manage staff", {"branch": "All stores"})
        rows = ui.texts("dataframe")[0]
        self.assertIn({"Username": "cara", "Store": "Sengkang"}, rows)
        ui, _ = self.show("Manage staff", {"branch": "All stores", "staff_user": "amy",
                                           "staff_password": STAFF_PASSWORD}, clicks={"staff_add"})
        self.assertIn("The username amy is already taken.", ui.texts("error"))
        self.show("Manage staff", {"branch": "All stores", "remove_user": "cara", "remove_user_sure_cara": True},
                  clicks={"remove_user_button"})
        self.assertIsNone(self.state["accounts"].find("cara"))

    def test_master_view_does_not_depend_on_the_class_object(self):
        """Streamlit can reload a module while a user is logged in, so the account in the
        session may come from an older copy of MasterAccount. The app asks the account
        (is_master) instead of checking its class, so the master still gets every store."""
        class OldCopyOfMasterAccount:
            def get_username(self): return "boss"
            def describe(self): return "Master (all stores)"
            def can_access(self, name): return True
            def is_master(self): return True
        self.state["user"] = OldCopyOfMasterAccount()
        ui, _ = self.show("Overview", {"branch": "All stores"})
        self.assertIn("All stores", ui.texts("subheader"))

    def test_employees_cannot_see_master_pages(self):
        self.log_in("amy")
        ui, _ = self.show("Manage staff", {"branch": "All stores"})
        self.assertNotIn("Manage staff", ui.texts("subheader"))
        self.assertIn("Kovan", ui.texts("header"))
