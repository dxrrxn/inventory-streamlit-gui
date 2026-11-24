"""Tests for the daily leftover stock: the snapshot, where it is saved, and the Daily stock page."""
import datetime
import json
import os

from app_test_case import AppTestCase, FakeDatabase
from brand import Brand
from daily_stock_record import DailyStockRecord
from face_product import FaceProduct
from fake_mongo import BrokenCollection, FakeCollection
from inventory import Inventory
from json_stock_history_store import JsonStockHistoryStore
from mongo_stock_history_store import MongoStockHistoryStore
from store_factory import StoreFactory

TODAY = DailyStockRecord.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)


def small_inventory() -> Inventory:
    inventory = Inventory()
    brand = Brand("Laneige")
    inventory.add_product(FaceProduct("F1", "Cream", 30, 8, brand, "Dry", par_level=10))
    inventory.add_product(FaceProduct("F2", "Mask", 40, 12, brand, "All", par_level=10))
    return inventory


class TestDailyStockRecord(AppTestCase):

    def test_snapshot_does_not_change_when_stock_changes_later(self):
        inventory = small_inventory()
        record = DailyStockRecord.from_inventory("Kovan", TODAY, inventory, "amy")
        inventory.find_product("F1").update_stock(0)
        self.assertEqual(record.stock_of("F1"), 8)
        self.assertEqual(record.total_units(), 20)
        self.assertEqual(record.below_par_count(), 1)

    def test_future_day_is_rejected(self):
        with self.assertRaises(ValueError):
            DailyStockRecord.from_inventory("Kovan", TODAY + datetime.timedelta(days=1),
                                            small_inventory(), "amy")

    def test_compare_with_the_previous_day(self):
        inventory = small_inventory()
        before = DailyStockRecord.from_inventory("Kovan", YESTERDAY, inventory, "amy")
        inventory.find_product("F1").update_stock(5)
        inventory.add_product(FaceProduct("F3", "Toner", 20, 7, Brand("Tatcha"), "Oily"))
        after = DailyStockRecord.from_inventory("Kovan", TODAY, inventory, "amy")
        changes = {row["id"]: row["change"] for row in after.compare_with(before)}
        self.assertEqual(changes, {"F1": -3, "F2": 0, "F3": None})       # F3 is new that day

    def test_saved_and_rebuilt(self):
        record = DailyStockRecord.from_inventory("Kovan", TODAY, small_inventory(), "amy")
        again = DailyStockRecord.from_dict(json.loads(json.dumps(record.to_dict())))
        self.assertEqual(again.get_day(), TODAY)
        self.assertEqual(again.get_counts(), record.get_counts())
        self.assertEqual(again.get_recorded_by(), "amy")


class TestHistoryStores(AppTestCase):

    def test_json_file_keeps_one_record_per_day(self):
        store = JsonStockHistoryStore(os.path.join(self.folder, "stores", "kovan_history.json"))
        self.assertEqual(store.load(), [])
        inventory = small_inventory()
        self.assertTrue(store.save(DailyStockRecord.from_inventory("Kovan", TODAY, inventory, "amy")))
        self.assertTrue(store.save(DailyStockRecord.from_inventory("Kovan", YESTERDAY, inventory, "amy")))
        inventory.find_product("F1").update_stock(1)
        self.assertTrue(store.save(DailyStockRecord.from_inventory("Kovan", TODAY, inventory, "ben")))
        records = store.load()
        self.assertEqual([r.get_day() for r in records], [YESTERDAY, TODAY])   # oldest first
        self.assertEqual(records[1].stock_of("F1"), 1)                         # today was replaced

    def test_damaged_json_is_an_error_and_damaged_days_are_skipped(self):
        path = os.path.join(self.folder, "history.json")
        with open(path, "w") as file:
            file.write("{oops")
        with self.assertRaises(OSError):
            JsonStockHistoryStore(path).load()
        good = DailyStockRecord.from_inventory("Kovan", TODAY, small_inventory(), "amy").to_dict()
        with open(path, "w") as file:
            json.dump([{"date": "not a date"}, good], file)
        self.assertEqual(len(JsonStockHistoryStore(path).load()), 1)

    def test_mongodb_collection(self):
        collection = FakeCollection("stock_history_kovan")
        store = MongoStockHistoryStore(collection, "test_db")
        store.save(DailyStockRecord.from_inventory("Kovan", TODAY, small_inventory(), "amy"))
        store.save(DailyStockRecord.from_inventory("Kovan", TODAY, small_inventory(), "amy"))
        self.assertEqual(len(collection.documents), 1)                # same day replaced, not added
        self.assertEqual(store.load()[0].total_units(), 20)
        broken = MongoStockHistoryStore(BrokenCollection(), "test_db")
        with self.assertRaises(OSError):
            broken.load()
        self.assertFalse(broken.save(store.load()[0]))

    def test_factory_gives_each_store_its_own_history(self):
        self.assertEqual(self.factory.history_store("Kovan").name, "JSON file (kovan_history.json)")
        database = FakeDatabase()
        factory = StoreFactory(self.folder, database, "test_db")
        factory.history_store("Punggol").save(
            DailyStockRecord.from_inventory("Punggol", TODAY, small_inventory(), "ben"))
        self.assertIn("stock_history_punggol", database)
        self.assertNotIn("stock_history_kovan", database)


class TestDailyStockPage(AppTestCase):

    def setUp(self):
        super().setUp()
        self.add_accounts()
        self.log_in("amy")

    def test_record_two_days_and_view_the_change(self):
        ui, _ = self.show("Daily stock")
        self.assertIn("No days recorded yet.", ui.texts("info"))
        _, rerun = self.show("Daily stock", {"daily_day": YESTERDAY}, clicks={"daily_record"})
        self.assertTrue(rerun)
        self.assertIn("Closing stock for", self.state["flash"])
        self.show("Update stock & PAR", {"stock_product": "F001", "stock_F001": 10}, clicks={"stock_button"})
        self.show("Daily stock", {"daily_day": TODAY}, clicks={"daily_record"})

        ui, _ = self.show("Daily stock")                                   # newest day shown first
        rows = {row["ID"]: row for row in ui.texts("dataframe")[0]}
        self.assertEqual(rows["F001"]["Leftover"], 10)
        self.assertEqual(rows["F001"]["Change"], "-8")                    # 18 yesterday, 10 today
        self.assertEqual(rows["F002"]["Change"], "+0")
        metrics = dict(ui.texts("metric"))
        self.assertEqual(metrics["Change since previous day"], "-8")
        self.assertEqual(ui.texts("line_chart")[0]["Units left"], [147, 139])          # all products together

        ui, _ = self.show("Daily stock", {"daily_view": YESTERDAY})       # look back at yesterday
        rows = {row["ID"]: row for row in ui.texts("dataframe")[0]}
        self.assertEqual(rows["F001"]["Leftover"], 18)
        self.assertEqual(rows["F001"]["Change"], "new")                   # first recorded day
        file_name, csv_text = ui.texts("download")[0]
        self.assertEqual(file_name, f"stock_kovan_{YESTERDAY.isoformat()}.csv")
        self.assertIn(f"Kovan,{YESTERDAY.isoformat()},F001,Laneige,Water Sleeping Mask,18,15,", csv_text)

    def test_recording_a_day_again_needs_the_tick_box(self):
        self.show("Daily stock", {"daily_day": TODAY}, clicks={"daily_record"})
        self.show("Update stock & PAR", {"stock_product": "F001", "stock_F001": 1}, clicks={"stock_button"})
        self.show("Daily stock", {"daily_day": TODAY}, clicks={"daily_record"})
        history = self.factory.history_store("Kovan").load()
        self.assertEqual(history[0].stock_of("F001"), 18)                 # not replaced without the tick
        self.show("Daily stock", {"daily_day": TODAY, f"daily_replace_{TODAY}": True}, clicks={"daily_record"})
        self.assertEqual(self.factory.history_store("Kovan").load()[0].stock_of("F001"), 1)

    def test_chart_for_one_product_shows_its_par(self):
        self.show("Daily stock", {"daily_day": TODAY}, clicks={"daily_record"})
        ui, _ = self.show("Daily stock", {"daily_chart": "M002"})
        chart = ui.texts("line_chart")[0]
        self.assertEqual((chart["Leftover"], chart["PAR"]), ([3], [10]))

    def test_each_store_has_its_own_history(self):
        self.show("Daily stock", {"daily_day": TODAY}, clicks={"daily_record"})
        self.log_in("ben")
        ui, _ = self.show("Daily stock")
        self.assertIn("No days recorded yet.", ui.texts("info"))
