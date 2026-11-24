import io
import os
from contextlib import redirect_stdout

from file_handler import load_inventory, save_inventory
from inventory import Inventory
from inventory_store import InventoryStore


class JsonInventoryStore(InventoryStore):
    """Keeps the inventory in a JSON file, using the lab's file_handler functions unchanged."""

    def __init__(self, path: str):
        self.__path: str = path

    @property
    def name(self) -> str:
        return f"JSON file ({os.path.basename(self.__path)})"

    def load(self, inventory: Inventory) -> str:
        output = io.StringIO()
        with redirect_stdout(output):          # file_handler prints its messages
            load_inventory(inventory, self.__path)
        return output.getvalue().strip()

    def save(self, inventory: Inventory) -> tuple[bool, str]:
        try:
            save_inventory(inventory, self.__path)
        except OSError as error:               # e.g. no permission or disk full
            return False, f"Could not save the inventory: {error}"
        return True, f"Inventory saved to {os.path.basename(self.__path)}."
