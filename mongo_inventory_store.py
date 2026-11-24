from pymongo.errors import PyMongoError

from inventory import Inventory
from inventory_store import InventoryStore
from product_factory import ProductFactory
from supplier import Supplier


class MongoInventoryStore(InventoryStore):
    """Keeps the inventory in a MongoDB collection: one document per product, in the
    same shape as inventory.json (product.to_dict()).

    Aggregation: it is given its collection, and optionally a store to copy the
    products from the first time, when the collection is still empty.
    """

    HIDE_ID = {"_id": 0}       # MongoDB's own _id is never passed to the products

    def __init__(self, collection, database_name: str, first_time_source: InventoryStore | None = None):
        self.__collection = collection
        self.__database_name: str = database_name
        self.__first_time_source = first_time_source
        self.__loaded: bool = False             # never save over data we couldn't read

    @property
    def name(self) -> str:
        return f"MongoDB ({self.__database_name})"

    def load(self, inventory: Inventory) -> str:
        try:
            documents = list(self.__collection.find({}, self.HIDE_ID).sort("_id", 1))
        except PyMongoError as error:
            return f"Could not read the products from MongoDB: {error}"
        self.__loaded = True
        if not documents and self.__first_time_source is not None:
            message = self.__first_time_source.load(inventory)
            return (f"{message}\nMongoDB is empty, so these products came from "
                    f"{self.__first_time_source.name}. Click Save inventory to store them in MongoDB.")

        suppliers: dict[str, Supplier] = {}     # products with the same supplier share one object
        loaded, skipped = 0, 0
        for document in documents:
            try:
                s = document["supplier"]
                if s["id"] not in suppliers:
                    suppliers[s["id"]] = Supplier(s["id"], s["name"], s["contact_email"])
                product = ProductFactory.create(
                    document["type"], document["id"], document["name"], document["price"],
                    document["stock"], suppliers[s["id"]],
                    weight=document.get("weight", 0.0),
                    download_size=document.get("download_size", 0.0))
            except (KeyError, TypeError, ValueError):
                skipped += 1                    # a damaged document doesn't stop the others
                continue
            if inventory.add_product(product):
                loaded += 1
        message = f"{loaded} products loaded from MongoDB."
        if skipped:
            message += f" {skipped} damaged record(s) skipped."
        return message

    def save(self, inventory: Inventory) -> tuple[bool, str]:
        if not self.__loaded:
            return False, ("Not saved: the products could not be read from MongoDB, "
                           "so saving now could delete them.")
        documents = [product.to_dict() for product in inventory.get_products()]
        keep = {document["id"] for document in documents}
        try:
            for document in documents:          # add new products, replace changed ones
                self.__collection.replace_one({"id": document["id"]}, document, upsert=True)
            for old in list(self.__collection.find({}, self.HIDE_ID)):
                if old.get("id") not in keep:   # removed in the GUI
                    self.__collection.delete_many({"id": old.get("id")})
        except PyMongoError as error:
            return False, f"Could not save to MongoDB: {error}"
        return True, f"{len(documents)} products saved to MongoDB."
