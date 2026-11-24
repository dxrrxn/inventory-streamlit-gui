"""Tests for where the inventory is kept: inventory.json or MongoDB.

MongoDB is replaced by a fake collection (tests/fake_mongo.py), so no database or
internet is needed. Each test uses a temporary copy of inventory.json.
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fake_mongo import BrokenCollection, FakeCollection
from fake_streamlit import FakeStreamlit, RerunRequested
from inventory import Inventory
from json_inventory_store import JsonInventoryStore
from mongo_inventory_store import MongoInventoryStore
from store_factory import StoreFactory
from streamlit_app import InventoryGui, APP_DIR


class StoreTestCase(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "inventory.json")
        shutil.copy(os.path.join(APP_DIR, "inventory.json"), self.path)
        self.json_store = JsonInventoryStore(self.path)

    def tearDown(self):
        shutil.rmtree(self.folder)

    @staticmethod
    def ids(inventory):
        return [product.get_product_id() for product in inventory.get_products()]


class TestMongoInventoryStore(StoreTestCase):

    def test_first_load_copies_the_json_products_then_save_stores_them(self):
        collection = FakeCollection("products")
        store = MongoInventoryStore(collection, "test_db", first_time_source=self.json_store)
        inventory = Inventory()
        message = store.load(inventory)
        self.assertIn("MongoDB is empty", message)
        self.assertEqual(self.ids(inventory), ["F001", "F002", "F003", "M001", "M002", "M003", "H001", "H002", "B001", "B002", "B003", "F004"])

        saved, message = store.save(inventory)
        self.assertTrue(saved)
        self.assertEqual(message, "12 products saved to MongoDB.")
        self.assertEqual([doc["id"] for doc in collection.documents], ["F001", "F002", "F003", "M001", "M002", "M003", "H001", "H002", "B001", "B002", "B003", "F004"])

    def test_reload_from_mongodb_keeps_categories_and_shared_brand(self):
        collection = FakeCollection("products")
        first = MongoInventoryStore(collection, "test_db", first_time_source=self.json_store)
        inventory = Inventory()
        first.load(inventory)
        first.save(inventory)

        again = Inventory()
        message = MongoInventoryStore(collection, "test_db").load(again)
        self.assertEqual(message, "12 products loaded from MongoDB.")
        perfume = again.find_product("B002")
        self.assertEqual(type(perfume).__name__, "BodyProduct")
        self.assertEqual(perfume.get_detail(), 100.0)
        self.assertIs(perfume.get_brand(), again.find_product("M003").get_brand())   # both Dior

    def test_save_updates_changed_and_deletes_removed_products(self):
        collection = FakeCollection("products")
        store = MongoInventoryStore(collection, "test_db", first_time_source=self.json_store)
        inventory = Inventory()
        store.load(inventory)
        store.save(inventory)
        inventory.find_product("F001").update_stock(99)
        inventory.remove_product("H002")
        store.save(inventory)
        by_id = {doc["id"]: doc for doc in collection.documents}
        self.assertEqual(len(by_id), 11)
        self.assertNotIn("H002", by_id)
        self.assertEqual(by_id["F001"]["stock"], 99)

    def test_damaged_document_is_skipped(self):
        collection = FakeCollection("products")
        collection.insert_one({"id": "X1", "name": "Broken"})          # no category, price or brand
        message = MongoInventoryStore(collection, "test_db").load(Inventory())
        self.assertEqual(message, "0 products loaded from MongoDB. 1 damaged record(s) skipped.")

    def test_lost_connection_is_reported_and_save_is_refused(self):
        store = MongoInventoryStore(BrokenCollection(), "test_db")
        inventory = Inventory()
        self.assertIn("Could not read the products from MongoDB", store.load(inventory))
        saved, message = store.save(inventory)
        self.assertFalse(saved)
        self.assertIn("saving now could delete them", message)


class TestStoreFactory(StoreTestCase):

    def setUp(self):
        super().setUp()
        patcher = patch("store_factory.load_dotenv", lambda: None)   # ignore the real .env
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_json_file_by_default(self):
        with patch.dict(os.environ, {"STORAGE": "json"}):
            store, warning = StoreFactory.from_env(self.path)
        self.assertEqual(store.name, "JSON file (inventory.json)")
        self.assertEqual(warning, "")

    def test_falls_back_to_json_without_uri_or_server(self):
        with patch.dict(os.environ, {"STORAGE": "mongo", "MONGODB_URI": ""}):
            store, warning = StoreFactory.from_env(self.path)
        self.assertEqual(store.name, "JSON file (inventory.json)")
        self.assertIn("MONGODB_URI is not set", warning)

        with patch.dict(os.environ, {"STORAGE": "mongo", "MONGODB_URI": "not-a-uri"}):
            store, warning = StoreFactory.from_env(self.path)
        self.assertEqual(store.name, "JSON file (inventory.json)")
        self.assertIn("Could not connect to MongoDB", warning)
        self.assertNotIn("not-a-uri", warning)           # the URI (with its password) is never shown

    def test_uses_mongodb_when_the_server_answers(self):
        class FakeClient:
            def __init__(self, uri, **options):
                self.admin = self

            def command(self, name):
                return {"ok": 1}

            def __getitem__(self, name):
                return {"products": FakeCollection("products")}

        env = {"STORAGE": "mongo", "MONGODB_URI": "mongodb://localhost:27017", "MONGODB_DATABASE": "shop"}
        with patch.dict(os.environ, env), patch("store_factory.MongoClient", FakeClient):
            store, warning = StoreFactory.from_env(self.path)
        self.assertEqual(store.name, "MongoDB (shop)")
        self.assertEqual(warning, "")


class TestGuiWithMongoDB(StoreTestCase):

    def test_sidebar_shows_the_storage_and_save_goes_to_mongodb(self):
        collection = FakeCollection("products")
        state = {}
        store = MongoInventoryStore(collection, "test_db", first_time_source=self.json_store)
        ui = FakeStreamlit(inputs={"page": "Products"}, session_state=state)
        InventoryGui(ui, store).run()
        self.assertIn("Storage: MongoDB (test_db)", ui.texts("caption"))

        ui = FakeStreamlit(inputs={"page": "Products"}, clicks={"save"}, session_state=state)
        with self.assertRaises(RerunRequested):          # the page redraws after saving
            InventoryGui(ui).run()
        self.assertEqual(len(collection.documents), 12)
        self.assertEqual(state["flash"], "12 products saved to MongoDB.")


if __name__ == "__main__":
    unittest.main()
