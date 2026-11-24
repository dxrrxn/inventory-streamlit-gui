from inventory import Inventory
from inventory_store import InventoryStore

BRANCH_NAMES = ("Sengkang", "Punggol", "Hougang", "Kovan", "Serangoon")


class Branch:
    """One Sephora store, e.g. Sengkang, with its own products, stock and PAR levels.

    Composition: the Branch creates and owns its Inventory.
    Aggregation: it is given the InventoryStore (JSON file or MongoDB) to load and save with.
    """

    def __init__(self, name: str, inventory_store: InventoryStore):
        if name not in BRANCH_NAMES:
            raise ValueError(f"Unknown store: {name}")
        self.__name: str = name
        self.__inventory_store: InventoryStore = inventory_store
        self.__inventory: Inventory = Inventory()
        self.__load_message: str = inventory_store.load(self.__inventory)

    @staticmethod
    def key(name: str) -> str:
        """The name used for this store's file or collection, e.g. "sengkang"."""
        return name.strip().lower().replace(" ", "_")

    def get_name(self) -> str:
        return self.__name

    def get_inventory(self) -> Inventory:
        return self.__inventory

    def get_load_message(self) -> str:
        return self.__load_message

    def get_storage_name(self) -> str:
        return self.__inventory_store.name

    def save(self) -> tuple[bool, str]:
        saved, message = self.__inventory_store.save(self.__inventory)
        return saved, f"{self.__name}: {message}"
