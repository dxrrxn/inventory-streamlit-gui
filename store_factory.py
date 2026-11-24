import os

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from inventory_store import InventoryStore
from json_inventory_store import JsonInventoryStore
from mongo_inventory_store import MongoInventoryStore


class StoreFactory:
    """Factory pattern: the one place that decides where the inventory is kept.

    Settings come from .env:  STORAGE=mongo, MONGODB_URI=... and optionally
    MONGODB_DATABASE=...  Without them, or if MongoDB can't be reached, the
    inventory.json file is used, so the app always starts.
    """

    DEFAULT_DATABASE = "sephora_inventory"
    COLLECTION = "products"
    TIMEOUT_MS = 5000              # give up after 5 seconds instead of hanging

    @classmethod
    def from_env(cls, json_path: str) -> tuple[InventoryStore, str]:
        """Returns the store to use and a warning for the screen ("" if none)."""
        load_dotenv()
        json_store = JsonInventoryStore(json_path)
        if os.environ.get("STORAGE", "json").strip().lower() != "mongo":
            return json_store, ""
        uri = os.environ.get("MONGODB_URI", "").strip()
        if not uri:
            return json_store, "STORAGE=mongo but MONGODB_URI is not set, so inventory.json is used."
        database = os.environ.get("MONGODB_DATABASE", "").strip() or cls.DEFAULT_DATABASE
        options = {"serverSelectionTimeoutMS": cls.TIMEOUT_MS}
        if uri.startswith("mongodb+srv://"):
            options["tlsCAFile"] = certifi.where()          # Atlas needs TLS certificates
        try:
            client = MongoClient(uri, **options)
            client.admin.command("ping")                   # check the server really answers
        except PyMongoError as error:
            # Only the error is shown, never the URI, because the URI holds the password.
            return json_store, f"Could not connect to MongoDB ({error}), so inventory.json is used."
        collection = client[database][cls.COLLECTION]
        return MongoInventoryStore(collection, database, first_time_source=json_store), ""
