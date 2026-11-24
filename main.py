from supplier import Supplier
from can_be_shipped import CanBeShipped
from inventory import Inventory, LINE
from order import Order
from product_factory import ProductFactory
from discount_strategy import DiscountStrategy, NoDiscount, PercentageDiscount, BulkDiscount
from student_discount import StudentDiscount
from file_handler import (load_inventory, save_inventory, load_products,
                          INVENTORY_FILE, PRODUCTS_CSV)

# Discount choices for the menu. The strategies hold no changing data,
# so every order that picks one can share the same object (association).
DISCOUNT_OPTIONS: dict[str, tuple[str, DiscountStrategy]] = {
    "1": ("No discount", NoDiscount()),
    "2": ("10% off", PercentageDiscount(10)),
    "3": ("$20 off orders of $200 or more", BulkDiscount(200, 20)),
    "4": ("Student discount (5% off)", StudentDiscount()),
}


# ---------- Input helpers ----------

def get_positive_float(prompt: str) -> float:
    """Keep asking until the user enters a number greater than zero."""
    while True:
        try:
            value = float(input(prompt))
            if value <= 0:
                print("Please enter a number greater than zero.")
                continue
            return value
        except ValueError:
            print("Please enter a valid number, e.g. 12.50")


def read_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Input cannot be empty.")


def read_number(prompt: str) -> float:
    """Keep asking until the user types a non-negative number (weight, size)."""
    while True:
        try:
            value = float(input(prompt))
            if value >= 0:
                return value
            print("Value cannot be negative.")
        except ValueError:
            print("Please enter a valid number.")


def read_stock(prompt: str) -> int:
    while True:
        try:
            value = int(input(prompt))
            if value >= 0:
                return value
            print("Stock cannot be negative.")
        except ValueError:
            print("Please enter a whole number.")


def read_quantity(prompt: str) -> int:
    while True:
        try:
            value = int(input(prompt))
            if value > 0:
                return value
            print("Quantity must be greater than zero.")
        except ValueError:
            print("Please enter a whole number.")


def read_product_type() -> str:
    """Return the product type name the ProductFactory understands."""
    while True:
        choice = input("Product type (1 = Physical, 2 = Digital): ").strip()
        if choice == "1":
            return "physical"
        if choice == "2":
            return "digital"
        print("Please enter 1 or 2.")


def read_discount() -> DiscountStrategy:
    print("Discount options:")
    for key, (label, _) in DISCOUNT_OPTIONS.items():
        print(f"{key}. {label}")
    while True:
        choice = input("Choose a discount: ").strip()
        if choice in DISCOUNT_OPTIONS:
            return DISCOUNT_OPTIONS[choice][1]
        print(f"Please enter a number from 1 to {len(DISCOUNT_OPTIONS)}.")


# ---------- Supplier lookup ----------

def find_supplier(inventory: Inventory, supplier_id: str) -> Supplier | None:
    """Reuse a Supplier object that an existing product already refers to."""
    for product in inventory.get_products():
        supplier = product.get_supplier()
        if supplier.get_supplier_id().upper() == supplier_id.upper():
            return supplier
    return None


def read_supplier(inventory: Inventory) -> Supplier:
    supplier_id = read_non_empty("Supplier ID: ")
    supplier = find_supplier(inventory, supplier_id)
    if supplier is not None:
        print(f"Using existing supplier: {supplier.get_name()}")
        return supplier
    name = read_non_empty("Supplier Name: ")
    email = read_non_empty("Supplier Email: ")
    return Supplier(supplier_id, name, email)


# ---------- Menu actions ----------

def add_product(inventory: Inventory) -> None:
    print("Add New Product")
    product_id = read_non_empty("Product ID: ")
    if inventory.find_product(product_id) is not None:
        print("A product with this ID already exists.")
        return
    product_type = read_product_type()
    name = read_non_empty("Product Name: ")
    price = get_positive_float("Price: ")
    stock = read_stock("Stock Quantity: ")
    supplier = read_supplier(inventory)

    weight = 0.0
    download_size = 0.0
    if product_type == "physical":
        weight = read_number("Weight (kg): ")
    else:
        download_size = read_number("Download Size (MB): ")

    product = ProductFactory.create(product_type, product_id, name, price, stock, supplier,
                                    weight=weight, download_size=download_size)
    inventory.add_product(product)
    print("Product added successfully!")


def remove_product(inventory: Inventory) -> None:
    print("Remove Product")
    product = inventory.remove_product(read_non_empty("Enter Product ID: "))
    if product is None:
        print("Product not found.")
        return
    print(f"{product.get_name()} removed from the inventory.")


def update_stock(inventory: Inventory) -> None:
    print("Update Stock")
    product = inventory.find_product(read_non_empty("Enter Product ID: "))
    if product is None:
        print("Product not found.")
        return
    print("Product Found:")
    print(f"Name: {product.get_name()}")
    print(f"Current Stock: {product.get_stock()}")
    product.update_stock(read_stock("New Stock Quantity: "))
    print("Stock updated successfully!")


def search_product(inventory: Inventory) -> None:
    print("Search Product")
    product = inventory.find_product(read_non_empty("Enter Product ID: "))
    if product is None:
        print("Product not found.")
        return
    print("Product Found")
    print(LINE)
    product.display_information()
    print(product.get_fulfilment_info())
    if isinstance(product, CanBeShipped):
        print(f"Shipping Cost: ${product.calculate_shipping_cost():.2f}")
    product.get_supplier().display_information()
    print(LINE)


def create_order(inventory: Inventory) -> None:
    print("Create Order")
    order = Order(read_non_empty("Order ID: "))
    while True:
        product_id = input("Product ID to add (leave blank to finish): ").strip()
        if not product_id:
            break
        product = inventory.find_product(product_id)
        if product is None:
            print("Product not found.")
            continue
        order.add_order_line(product, read_quantity("Quantity: "))
        print(f"Added {product.get_name()}.")
    order.set_discount(read_discount())
    print(LINE)
    order.display_order()
    print(LINE)


def import_products(inventory: Inventory) -> None:
    print("Load Products from CSV")
    path = input(f"CSV file (leave blank for {PRODUCTS_CSV}): ").strip() or PRODUCTS_CSV
    print("Every product in the file will use this supplier.")
    supplier = read_supplier(inventory)
    load_products(path, inventory, supplier)


def print_menu() -> None:
    print("----------- MENU -----------")
    print("1. Display All Products")
    print("2. Add Product")
    print("3. Remove Product")
    print("4. Update Stock")
    print("5. Search Product")
    print("6. Create Order")
    print("7. Load Products from CSV")
    print("8. Save Inventory")
    print("9. Exit")
    print("----------------------------")


def run_menu(inventory: Inventory) -> None:
    while True:
        print_menu()
        option = input("Enter option: ").strip()
        if option == "1":
            inventory.display_all_products()
        elif option == "2":
            add_product(inventory)
        elif option == "3":
            remove_product(inventory)
        elif option == "4":
            update_stock(inventory)
        elif option == "5":
            search_product(inventory)
        elif option == "6":
            create_order(inventory)
        elif option == "7":
            import_products(inventory)
        elif option == "8":
            print("Saving inventory...")
            save_inventory(inventory)
            print(f"Inventory saved successfully to {INVENTORY_FILE}.")
        elif option == "9":
            print("Saving inventory before exit...")
            save_inventory(inventory)
            print("Inventory saved successfully.")
            print("Program exited.")
            break
        else:
            print("Invalid option. Please enter a number from 1 to 9.")


def main() -> None:
    print("=" * 40)
    print("INVENTORY MANAGEMENT SYSTEM")
    print("=" * 40)
    inventory = Inventory()
    load_inventory(inventory)
    run_menu(inventory)


if __name__ == "__main__":
    main()