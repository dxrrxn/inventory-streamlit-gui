from abc import ABC, abstractmethod

from inventory import Inventory


class InventoryStore(ABC):
    """Interface: somewhere the inventory is loaded from and saved to.

    JsonInventoryStore uses inventory.json and MongoInventoryStore uses a MongoDB
    collection. The GUI only calls these methods, so either one can be used
    (Liskov Substitution Principle).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Where the products are kept, shown in the sidebar."""

    @abstractmethod
    def load(self, inventory: Inventory) -> str:
        """Add the saved products to the inventory. Returns a message for the screen."""

    @abstractmethod
    def save(self, inventory: Inventory) -> tuple[bool, str]:
        """Save every product. Returns (True if it worked, a message for the screen)."""
