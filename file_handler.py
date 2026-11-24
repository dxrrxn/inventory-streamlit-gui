import csv
import json

from inventory import Inventory
from product_factory import ProductFactory

INVENTORY_FILE = "inventory.json"
PRODUCTS_CSV = "products.csv"
CSV_COLUMNS = ["category", "product_id", "name", "brand", "price", "stock_quantity", "detail"]


def load_inventory(inventory: Inventory, filename: str = INVENTORY_FILE) -> None:
    """Read products from the JSON file and add them to the Inventory through the ProductFactory.

    Products of the same brand share one Brand object, like they did before saving.
    """
    try:
        with open(filename, "r") as file:
            data = json.load(file)
        brands = inventory.get_brands()
        for item in data:
            inventory.add_product(ProductFactory.from_dict(item, brands))
        print(f"{filename} found.")
        print("Inventory loaded successfully.")
    except FileNotFoundError:
        print(f"{filename} not found. Starting with a new inventory.")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        print(f"{filename} is corrupted. Starting with a new inventory.")


def save_inventory(inventory: Inventory, filename: str = INVENTORY_FILE) -> None:
    """Write every product in the Inventory (with its category and brand) to the JSON file."""
    data = [product.to_dict() for product in inventory.get_products()]
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)


def load_products(path: str, inventory: Inventory) -> None:
    """Load products from a CSV file with the columns in CSV_COLUMNS.
    Bad rows are reported and skipped; good rows still load."""
    try:
        file = open(path, newline="")
    except FileNotFoundError:
        print(f"Products file not found: {path}")
    else:
        loaded = 0
        brands = inventory.get_brands()       # reuse brands that are already in the inventory
        with file:
            reader = csv.reader(file)
            next(reader, None)                                  # skip the header row
            for row_number, row in enumerate(reader, start=2):  # row 1 is the header
                try:
                    if len(row) != len(CSV_COLUMNS):
                        raise ValueError(f"expected {len(CSV_COLUMNS)} columns, found {len(row)}")
                    category, product_id, name, brand_name, price, stock_quantity, detail = row
                    record = {"category": category, "id": product_id, "name": name,
                              "brand": {"name": brand_name}, "price": float(price),
                              "stock": int(stock_quantity), "detail": detail}
                    product = ProductFactory.from_dict(record, brands)
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
