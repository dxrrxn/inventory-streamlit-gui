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
from inventory import Inventory
from json_inventory_store import JsonInventoryStore
from mongo_inventory_store import MongoInventoryStore
from store_factory import StoreFactory
from streamlit_app import APP_DIR
from app_test_case import AppTestCase, FakeDatabase, MASTER_PASSWORD, STAFF_PASSWORD


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


class TestJsonInventoryStore(StoreTestCase):

    def test_new_store_starts_from_the_sample_and_saves_to_its_own_file(self):
        path = os.path.join(self.folder, "stores", "kovan.json")
        store = JsonInventoryStore(path, first_time_source=self.json_store)
        inventory = Inventory()
        self.assertIn("No saved inventory yet", store.load(inventory))
        self.assertEqual(len(inventory.get_products()), 12)
        inventory.remove_product("F001")
        self.assertTrue(store.save(inventory)[0])             # creates the stores/ folder
        again = Inventory()
        self.assertNotIn("No saved inventory yet", store.load(again))
        self.assertEqual(len(again.get_products()), 11)


class TestStoreFactory(AppTestCase):

    def setUp(self):
        super().setUp()
        patcher = patch("store_factory.load_dotenv", lambda: None)   # ignore the real .env
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_json_files_by_default_one_per_store(self):
        with patch.dict(os.environ, {"STORAGE": "json"}):
            factory, warning = StoreFactory.from_env(self.folder)
        self.assertFalse(factory.uses_mongo)
        self.assertEqual(warning, "")
        self.assertEqual(factory.inventory_store("Kovan").name, "JSON file (kovan.json)")
        self.assertEqual(factory.inventory_store("Serangoon").name, "JSON file (serangoon.json)")

    def test_falls_back_to_json_without_uri_or_server(self):
        with patch.dict(os.environ, {"STORAGE": "mongo", "MONGODB_URI": ""}):
            factory, warning = StoreFactory.from_env(self.folder)
        self.assertFalse(factory.uses_mongo)
        self.assertIn("MONGODB_URI is not set", warning)

        with patch.dict(os.environ, {"STORAGE": "mongo", "MONGODB_URI": "not-a-uri"}):
            factory, warning = StoreFactory.from_env(self.folder)
        self.assertFalse(factory.uses_mongo)
        self.assertIn("Could not connect to MongoDB", warning)
        self.assertNotIn("not-a-uri", warning)           # the URI (with its password) is never shown

    def test_uses_mongodb_when_the_server_answers(self):
        database = FakeDatabase()

        class FakeClient:
            def __init__(self, uri, **options):
                self.admin = self

            def command(self, name):
                return {"ok": 1}

            def __getitem__(self, name):
                return database

        env = {"STORAGE": "mongo", "MONGODB_URI": "mongodb://localhost:27017", "MONGODB_DATABASE": "shop"}
        with patch.dict(os.environ, env), patch("store_factory.MongoClient", FakeClient):
            factory, warning = StoreFactory.from_env(self.folder)
        self.assertTrue(factory.uses_mongo)
        self.assertEqual(warning, "")
        self.assertEqual(factory.inventory_store("Hougang").name, "MongoDB (shop)")
        factory.inventory_store("Hougang").load(Inventory())
        self.assertIn("products_hougang", database)


class TestSampleData(AppTestCase):

    def test_each_store_starts_from_its_own_sample_file(self):
        os.makedirs(os.path.join(self.folder, "sample_data"))
        shutil.copy(os.path.join(APP_DIR, "sample_data", "hougang.json"),
                    os.path.join(self.folder, "sample_data", "hougang.json"))
        hougang, kovan = Inventory(), Inventory()
        self.assertIn("hougang.json", self.factory.inventory_store("Hougang").load(hougang))
        self.assertIn("inventory.json", self.factory.inventory_store("Kovan").load(kovan))   # no sample: the default
        self.assertEqual(len(hougang.get_products()), 10)
        self.assertEqual(len(kovan.get_products()), 12)

    def test_the_five_sample_files_are_different(self):
        contents = set()
        for name in ("sengkang", "punggol", "hougang", "kovan", "serangoon"):
            inventory = Inventory()
            JsonInventoryStore(os.path.join(APP_DIR, "sample_data", f"{name}.json")).load(inventory)
            self.assertGreater(len(inventory.get_products()), 0)
            contents.add(tuple((p.get_product_id(), p.get_stock()) for p in inventory.get_products()))
        self.assertEqual(len(contents), 5)


class TestGuiWithMongoDB(AppTestCase):

    def make_factory(self):
        self.database = FakeDatabase()
        return StoreFactory(self.folder, self.database, "test_db")

    def test_accounts_and_each_store_have_their_own_collections(self):
        self.add_accounts()
        self.assertEqual([doc["username"] for doc in self.database["accounts"].documents],
                         ["boss", "amy", "ben"])
        saved = str(self.database["accounts"].documents)
        self.assertNotIn(MASTER_PASSWORD, saved)                 # only hashes are stored
        self.assertNotIn(STAFF_PASSWORD, saved)

        self.log_in("amy")
        ui, _ = self.show("Products")
        self.assertIn("Storage: MongoDB (test_db)", ui.texts("caption"))
        self.show("Update stock & PAR", {**self.pick("stock", "F001"), "stock_F001": 1}, clicks={"stock_button"})
        _, rerun = self.show("Products", clicks={"save"})
        self.assertTrue(rerun)
        self.assertEqual(self.state["flash"], "Kovan: 12 products saved to MongoDB.")
        kovan = {doc["id"]: doc for doc in self.database["products_kovan"].documents}
        self.assertEqual(kovan["F001"]["stock"], 1)
        self.assertEqual(self.database["products_punggol"].documents, [])   # other stores untouched


if __name__ == "__main__":
    unittest.main()
