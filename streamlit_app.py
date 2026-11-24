"""
Streamlit web GUI for the Week 11 Inventory Management System.

Run with:  streamlit run streamlit_app.py

The GUI only replaces the terminal menu in main.py. It reuses the lab's classes
unchanged: Inventory, ProductFactory, Order, the DiscountStrategy classes and the
functions in file_handler.py.
"""
from __future__ import annotations

import io
import os
import tempfile
from contextlib import redirect_stdout

from can_be_shipped import CanBeShipped
from file_handler import load_inventory, save_inventory, load_products
from inventory import Inventory
from main import DISCOUNT_OPTIONS
from order import Order
from product import Product
from product_factory import ProductFactory
from supplier import Supplier

APP_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_PATH = os.path.join(APP_DIR, "inventory.json")
PRODUCTS_CSV_PATH = os.path.join(APP_DIR, "products.csv")
NEW_SUPPLIER = "+ New supplier"


class InventoryGui:
    """One page per menu option. Streamlit re-runs the whole script after every
    click, so the Inventory and the order being built are kept in session_state.

    The Streamlit module is passed in as `ui` (dependency injection), so the tests
    can use a fake one instead of a browser.
    """

    PAGES = ("Products", "Add product", "Update stock", "Remove product",
             "Search product", "Create order", "Import from CSV")

    def __init__(self, ui, inventory_path: str = INVENTORY_PATH):
        self.__ui = ui
        self.__inventory_path = inventory_path
        state = ui.session_state
        if "inventory" not in state:
            inventory = Inventory()
            messages = self.__captured(load_inventory, inventory, inventory_path)
            state["inventory"] = inventory
            state["order_lines"] = []          # (product_id, quantity) pairs
            state["unsaved"] = False
            state["flash"] = messages
        self.__inventory: Inventory = state["inventory"]

    @staticmethod
    def __captured(function, *args) -> str:
        """Run a file_handler function and return what it printed, to show on screen."""
        output = io.StringIO()
        with redirect_stdout(output):
            function(*args)
        return output.getvalue().strip()

    def __finish(self, message: str, changed: bool = True) -> None:
        """Remember a message, mark unsaved changes and redraw the page."""
        self.__ui.session_state["flash"] = message
        if changed:
            self.__ui.session_state["unsaved"] = True
        self.__ui.rerun()

    def __product_label(self, product_id: str) -> str:
        product = self.__inventory.find_product(product_id)
        return f"{product_id} - {product.get_name()}" if product else product_id

    def __product_ids(self) -> list[str]:
        return [product.get_product_id() for product in self.__inventory.get_products()]

    # ---------- page layout ----------

    def run(self) -> None:
        ui = self.__ui
        ui.set_page_config(page_title="Inventory Management System", layout="wide")
        ui.title("Inventory Management System")
        flash = ui.session_state.pop("flash", "")
        if flash:
            ui.info(flash)

        page = ui.sidebar.radio("Menu", self.PAGES, key="page")
        ui.sidebar.divider()
        if ui.session_state.get("unsaved"):
            ui.sidebar.warning("You have unsaved changes.")
        if ui.sidebar.button("Save inventory", key="save"):
            save_inventory(self.__inventory, self.__inventory_path)
            ui.session_state["unsaved"] = False
            self.__finish(f"Inventory saved to {os.path.basename(self.__inventory_path)}.", changed=False)

        {"Products": self.__products, "Add product": self.__add, "Update stock": self.__update_stock,
         "Remove product": self.__remove, "Search product": self.__search,
         "Create order": self.__order, "Import from CSV": self.__import}[page]()

    # ---------- 1. display all products ----------

    def __products(self) -> None:
        ui = self.__ui
        ui.subheader("Current inventory")
        products = self.__inventory.get_products()
        if not products:
            ui.info("Inventory is empty.")
            return
        first, second = ui.columns(2)
        first.metric("Products", len(products))
        second.metric("Stock value", f"${sum(p.get_price() * p.get_stock() for p in products):,.2f}")
        ui.dataframe([self.__row(product) for product in products], hide_index=True)

    @staticmethod
    def __row(product: Product) -> dict:
        """One table row. POLYMORPHISM: get_fulfilment_info() differs by product type."""
        shipping = (f"${product.calculate_shipping_cost():.2f}"
                    if isinstance(product, CanBeShipped) else "-")
        return {"ID": product.get_product_id(), "Name": product.get_name(),
                "Type": type(product).__name__.replace("Product", ""),
                "Price": f"${product.get_price():.2f}", "Stock": product.get_stock(),
                "Supplier": product.get_supplier().get_name(), "Shipping": shipping,
                "Fulfilment": product.get_fulfilment_info()}

    # ---------- 2. add product ----------

    def __choose_supplier(self, key: str) -> Supplier | None:
        """Pick an existing supplier (shared object, like main.find_supplier) or type a new one."""
        ui = self.__ui
        suppliers: dict[str, Supplier] = {}
        for product in self.__inventory.get_products():
            supplier = product.get_supplier()
            suppliers.setdefault(supplier.get_supplier_id(), supplier)
        options = [f"{sid} - {s.get_name()}" for sid, s in suppliers.items()] + [NEW_SUPPLIER]
        choice = ui.selectbox("Supplier", options, key=f"{key}_supplier")
        if choice != NEW_SUPPLIER:
            return suppliers[choice.split(" - ")[0]]
        supplier_id = ui.text_input("Supplier ID", key=f"{key}_sid").strip()
        name = ui.text_input("Supplier name", key=f"{key}_sname").strip()
        email = ui.text_input("Supplier email", key=f"{key}_semail").strip()
        if not (supplier_id and name and email):
            return None
        for existing_id, supplier in suppliers.items():
            if existing_id.upper() == supplier_id.upper():
                return supplier                    # reuse it instead of making a copy
        return Supplier(supplier_id, name, email)

    def __add(self) -> None:
        ui = self.__ui
        ui.subheader("Add new product")
        product_type = ui.radio("Product type", ["physical", "digital"], key="add_type",
                                format_func=str.capitalize, horizontal=True)
        product_id = ui.text_input("Product ID", key="add_id").strip()
        name = ui.text_input("Product name", key="add_name").strip()
        price = ui.number_input("Price ($)", min_value=0.01, value=1.00, step=0.50, key="add_price")
        stock = int(ui.number_input("Stock quantity", min_value=0, value=0, step=1, key="add_stock"))
        if product_type == "physical":
            weight = ui.number_input("Weight (kg)", min_value=0.0, value=0.0, step=0.1, key="add_weight")
            size = 0.0
        else:
            weight = 0.0
            size = ui.number_input("Download size (MB)", min_value=0.0, value=0.0, step=10.0, key="add_size")
        supplier = self.__choose_supplier("add")
        if not ui.button("Add product", key="add_button", type="primary"):
            return
        if not product_id or not name:
            ui.error("Product ID and name cannot be empty.")
        elif self.__inventory.find_product(product_id) is not None:
            ui.error("A product with this ID already exists.")
        elif supplier is None:
            ui.error("Fill in the supplier ID, name and email.")
        else:
            try:
                product = ProductFactory.create(product_type, product_id, name, price, stock,
                                                supplier, weight=weight, download_size=size)
            except ValueError as error:          # the product classes explain what is wrong
                ui.error(str(error))
                return
            self.__inventory.add_product(product)
            self.__finish(f"{name} added successfully.")

    # ---------- 3. update stock / 4. remove ----------

    def __pick_product(self, key: str) -> Product | None:
        ids = self.__product_ids()
        if not ids:
            self.__ui.info("Inventory is empty.")
            return None
        chosen = self.__ui.selectbox("Product", ids, key=key, format_func=self.__product_label)
        return self.__inventory.find_product(chosen)

    def __update_stock(self) -> None:
        ui = self.__ui
        ui.subheader("Update stock")
        product = self.__pick_product("stock_product")
        if product is None:
            return
        ui.write(f"Current stock: **{product.get_stock()}**")
        new_stock = int(ui.number_input("New stock quantity", min_value=0, value=product.get_stock(),
                                        step=1, key=f"stock_{product.get_product_id()}"))
        if ui.button("Update stock", key="stock_button", type="primary"):
            product.update_stock(new_stock)
            self.__finish(f"Stock for {product.get_name()} updated to {new_stock}.")

    def __remove(self) -> None:
        ui = self.__ui
        ui.subheader("Remove product")
        product = self.__pick_product("remove_product")
        if product is None:
            return
        sure = ui.checkbox(f"Yes, remove {product.get_name()}",
                           key=f"remove_sure_{product.get_product_id()}")   # one tick box per product
        if ui.button("Remove product", key="remove_button", disabled=not sure):
            removed = self.__inventory.remove_product(product.get_product_id())
            self.__finish(f"{removed.get_name()} removed from the inventory.")

    # ---------- 5. search ----------

    def __search(self) -> None:
        ui = self.__ui
        ui.subheader("Search product")
        product_id = ui.text_input("Product ID", key="search_id", placeholder="e.g. P001").strip()
        if not product_id:
            return
        product = self.__inventory.find_product(product_id)
        if product is None:
            ui.warning("Product not found.")
            return
        supplier = product.get_supplier()
        details = [("Name", product.get_name()), ("Price", f"${product.get_price():.2f}"),
                   ("Stock", str(product.get_stock())), ("Fulfilment", product.get_fulfilment_info())]
        if isinstance(product, CanBeShipped):     # only physical products can be shipped
            details.append(("Weight", f"{product.get_weight():.2f} kg"))
            details.append(("Shipping cost", f"${product.calculate_shipping_cost():.2f}"))
        else:
            details.append(("Download size", f"{product.get_download_size():.2f} MB"))
        details.append(("Supplier", f"{supplier.get_name()} ({supplier.get_supplier_id()}, "
                                    f"{supplier.get_contact_email()})"))
        ui.success(f"Found {product.get_product_id()}")
        ui.dataframe([{"Detail": label, "Value": value} for label, value in details], hide_index=True)

    # ---------- 6. create order ----------

    def __order(self) -> None:
        ui = self.__ui
        state = ui.session_state
        ui.subheader("Create order")
        order_id = ui.text_input("Order ID", value="O001", key="order_id").strip() or "O001"
        ids = self.__product_ids()
        if ids:
            first, second = ui.columns(2)
            chosen = first.selectbox("Product", ids, key="order_product", format_func=self.__product_label)
            quantity = int(second.number_input("Quantity", min_value=1, value=1, step=1, key="order_qty"))
            if ui.button("Add to order", key="order_add"):
                state["order_lines"] = state["order_lines"] + [(chosen, quantity)]

        # COMPOSITION: the Order creates its own OrderLines from the chosen products.
        labels = [label for label, _ in DISCOUNT_OPTIONS.values()]
        label = ui.selectbox("Discount", labels, key="order_discount")
        discount = next(strategy for name, strategy in DISCOUNT_OPTIONS.values() if name == label)
        order = Order(order_id, discount)            # STRATEGY: the Order just calls apply()
        for product_id, quantity in state["order_lines"]:
            product = self.__inventory.find_product(product_id)
            if product is not None:                  # skip products removed since
                order.add_order_line(product, quantity)

        lines = order.get_order_lines()
        if not lines:
            ui.info("No items yet. Choose a product and click Add to order.")
            return
        ui.dataframe([{"ID": line.get_product().get_product_id(), "Name": line.get_product().get_name(),
                       "Qty": line.get_quantity(), "Unit price": f"${line.get_product().get_price():.2f}",
                       "Subtotal": f"${line.calculate_subtotal():.2f}"} for line in lines], hide_index=True)
        first, second, third = ui.columns(3)
        first.metric("Subtotal", f"${order.calculate_subtotal():.2f}")
        second.metric("Discount", type(order.get_discount()).__name__)
        third.metric("Total", f"${order.calculate_total():.2f}")
        if ui.button("Clear order", key="order_clear"):
            state["order_lines"] = []
            self.__finish("Order cleared.", changed=False)

    # ---------- 7. import from CSV ----------

    def __import(self) -> None:
        ui = self.__ui
        ui.subheader("Load products from CSV")
        ui.caption("Columns: product_type, product_id, name, price, stock_quantity. "
                   "Bad rows are skipped and reported; good rows still load.")
        uploaded = ui.file_uploader("CSV file (leave empty to use products.csv)", type=["csv"],
                                    key="csv_file")
        ui.write("Every product in the file will use this supplier:")
        supplier = self.__choose_supplier("csv")
        if not ui.button("Import products", key="csv_button", type="primary"):
            return
        if supplier is None:
            ui.error("Fill in the supplier ID, name and email.")
            return
        if uploaded is None:
            messages = self.__captured(load_products, PRODUCTS_CSV_PATH, self.__inventory, supplier)
        else:
            with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as file:
                file.write(uploaded.getvalue())
            try:
                messages = self.__captured(load_products, file.name, self.__inventory, supplier)
            finally:
                os.remove(file.name)
        self.__finish(messages)


if __name__ == "__main__":
    import streamlit
    InventoryGui(streamlit).run()
