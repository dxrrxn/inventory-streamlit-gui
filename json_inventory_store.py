import io
import os
from contextlib import redirect_stdout

from file_handler import load_inventory, save_inventory
from inventory import Inventory
from inventory_store import InventoryStore


class JsonInventoryStore(InventoryStore):
    """Keeps the inventory in a JSON file, using the lab's file_handler functions unchanged.

    If the file doesn't exist yet, the products can be copied from another store
    the first time (e.g. the sample inventory.json for a new branch).
    """

    def __init__(self, path: str, first_time_source: InventoryStore | None = None):
        self.__path: str = path
        self.__first_time_source = first_time_source

    @property
    def name(self) -> str:
        return f"JSON file ({os.path.basename(self.__path)})"

    def load(self, inventory: Inventory) -> str:
        if not os.path.exists(self.__path) and self.__first_time_source is not None:
            message = self.__first_time_source.load(inventory)
            return (f"{message}\nNo saved inventory yet, so these products came from "
                    f"{self.__first_time_source.name}. Click Save inventory to keep them.")
        output = io.StringIO()
        with redirect_stdout(output):          # file_handler prints its messages
            load_inventory(inventory, self.__path)
        return output.getvalue().strip()

    def save(self, inventory: Inventory) -> tuple[bool, str]:
        try:
            folder = os.path.dirname(self.__path)
            if folder:
                os.makedirs(folder, exist_ok=True)     # e.g. the stores/ folder on first save
            save_inventory(inventory, self.__path)
        except OSError as error:               # e.g. no permission or disk full
            return False, f"Could not save the inventory: {error}"
        return True, f"Inventory saved to {os.path.basename(self.__path)}."
