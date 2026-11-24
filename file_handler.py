import csv
import json

from inventory import Inventory
from supplier import Supplier
from product_factory import ProductFactory

INVENTORY_FILE = "inventory.json"
PRODUCTS_CSV = "products.csv"


def load_inventory(inventory: Inventory, filename: str = INVENTORY_FILE) -> None:
    """Read products from the JSON file and add them to the Inventory through the ProductFactory.

    Products with the same supplier ID share one Supplier object, like they did before saving.
    """
    try:
        with open(filename, "r") as file:
            data = json.load(file)
        suppliers: dict[str, Supplier] = {}
        for item in data:
            s = item["supplier"]
            if s["id"] not in suppliers:
                suppliers[s["id"]] = Supplier(s["id"], s["name"], s["contact_email"])
            product = ProductFactory.create(
                item["type"], item["id"], item["name"], item["price"], item["stock"],
                suppliers[s["id"]],
                weight=item.get("weight", 0.0),
                download_size=item.get("download_size", 0.0),
            )
            inventory.add_product(product)
        print(f"{filename} found.")
        print("Inventory loaded successfully.")
    except FileNotFoundError:
        print(f"{filename} not found. Starting with a new inventory.")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        print(f"{filename} is corrupted. Starting with a new inventory.")


def save_inventory(inventory: Inventory, filename: str = INVENTORY_FILE) -> None:
    """Write every product in the Inventory (with its type and supplier) to the JSON file."""
    data = [product.to_dict() for product in inventory.get_products()]
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)


def load_products(path: str, inventory: Inventory, supplier: Supplier) -> None:
    """Load products from a CSV file. Bad rows are reported and skipped; good rows still load."""
    try:
        file = open(path, newline="")
    except FileNotFoundError:
        print(f"Products file not found: {path}")
    else:
        loaded = 0
        with file:
            reader = csv.reader(file)
            next(reader, None)                                  # skip the header row
            for row_number, row in enumerate(reader, start=2):  # row 1 is the header
                try:
                    product_type, product_id, name, price, stock_quantity = row
                    product = ProductFactory.create(product_type, product_id, name,
                                                    float(price), int(stock_quantity), supplier)
                except ValueError as error:
                    print(f"Row {row_number} skipped: {error}")
                    continue
                if inventory.add_product(product):
                    loaded += 1
                else:
                    print(f"Row {row_number} skipped: product {product_id} already exists.")
        print(f"{loaded} products loaded.")
    finally:
        print("Load attempt finished.")