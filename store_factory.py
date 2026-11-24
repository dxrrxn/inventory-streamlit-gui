import os

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from account_store import AccountStore
from branch import Branch
from inventory_store import InventoryStore
from json_account_store import JsonAccountStore
from json_inventory_store import JsonInventoryStore
from mongo_account_store import MongoAccountStore
from mongo_inventory_store import MongoInventoryStore
from json_stock_history_store import JsonStockHistoryStore
from mongo_stock_history_store import MongoStockHistoryStore
from stock_history_store import StockHistoryStore


class StoreFactory:
    """Factory pattern: the one place that decides where data is kept.

    Settings come from .env:  STORAGE=mongo, MONGODB_URI=... and optionally
    MONGODB_DATABASE=...  Without them, or if MongoDB can't be reached, JSON
    files are used, so the app always starts:
        stores/<store>.json            each store's products
        stores/<store>_history.json    each store's daily leftover stock
        accounts.json                  the login accounts (hashed passwords)
    In MongoDB each store has products_<store> and stock_history_<store>
    collections, plus one accounts collection.
    A store with no saved products yet starts from its own sample file in
    sample_data/ (or from inventory.json if there isn't one), so each store
    begins with different products and stock.
    """

    DEFAULT_DATABASE = "sephora_inventory"
    TIMEOUT_MS = 5000              # give up after 5 seconds instead of hanging

    def __init__(self, app_dir: str, database=None, database_name: str = ""):
        self.__app_dir: str = app_dir
        self.__database = database             # None means: use the JSON files
        self.__database_name: str = database_name

    @property
    def uses_mongo(self) -> bool:
        return self.__database is not None

    def __sample(self, key: str) -> InventoryStore:
        """The products a store starts with before it is first saved."""
        path = os.path.join(self.__app_dir, "sample_data", f"{key}.json")
        if not os.path.exists(path):
            path = os.path.join(self.__app_dir, "inventory.json")
        return JsonInventoryStore(path)

    def inventory_store(self, branch_name: str) -> InventoryStore:
        key = Branch.key(branch_name)
        if self.__database is None:
            path = os.path.join(self.__app_dir, "stores", f"{key}.json")
            return JsonInventoryStore(path, first_time_source=self.__sample(key))
        return MongoInventoryStore(self.__database[f"products_{key}"], self.__database_name,
                                   first_time_source=self.__sample(key))

    def history_store(self, branch_name: str) -> StockHistoryStore:
        key = Branch.key(branch_name)
        if self.__database is None:
            return JsonStockHistoryStore(os.path.join(self.__app_dir, "stores", f"{key}_history.json"))
        return MongoStockHistoryStore(self.__database[f"stock_history_{key}"], self.__database_name)

    def account_store(self) -> AccountStore:
        if self.__database is None:
            return JsonAccountStore(os.path.join(self.__app_dir, "accounts.json"))
        return MongoAccountStore(self.__database["accounts"])

    @classmethod
    def from_env(cls, app_dir: str) -> tuple["StoreFactory", str]:
        """Returns the factory to use and a warning for the screen ("" if none)."""
        load_dotenv()
        if os.environ.get("STORAGE", "json").strip().lower() != "mongo":
            return cls(app_dir), ""
        uri = os.environ.get("MONGODB_URI", "").strip()
        if not uri:
            return cls(app_dir), "STORAGE=mongo but MONGODB_URI is not set, so JSON files are used."
        database = os.environ.get("MONGODB_DATABASE", "").strip() or cls.DEFAULT_DATABASE
        options = {"serverSelectionTimeoutMS": cls.TIMEOUT_MS}
        if uri.startswith("mongodb+srv://"):
            options["tlsCAFile"] = certifi.where()          # Atlas needs TLS certificates
        try:
            client = MongoClient(uri, **options)
            client.admin.command("ping")                   # check the server really answers
        except PyMongoError as error:
            # Only the error is shown, never the URI, because the URI holds the password.
            return cls(app_dir), f"Could not connect to MongoDB ({error}), so JSON files are used."
        return cls(app_dir, client[database], database), ""
