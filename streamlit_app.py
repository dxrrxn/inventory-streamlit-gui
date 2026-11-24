"""
Streamlit web GUI for the Sephora Inventory Tracker.

Run with:  streamlit run streamlit_app.py

The GUI replaces the terminal menu in main.py and uses the same classes: Inventory,
ProductFactory (Face, Makeup, Hair and Body products), Brand, Order, the
DiscountStrategy classes and file_handler.py. StoreFactory decides whether the
products are kept in inventory.json or in MongoDB (see .env.example).
"""
from __future__ import annotations

import csv
import io
import os
import tempfile
from contextlib import redirect_stdout

from brand import Brand
from face_product import FaceProduct
from file_handler import load_products, CSV_COLUMNS
from hair_product import HairProduct
from inventory import Inventory
from inventory_store import InventoryStore
from main import DISCOUNT_OPTIONS
from order import Order
from product import Product, DEFAULT_PAR_LEVEL
from product_factory import ProductFactory
from store_factory import StoreFactory

APP_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_PATH = os.path.join(APP_DIR, "inventory.json")
PRODUCTS_CSV_PATH = os.path.join(APP_DIR, "products.csv")
NEW_BRAND = "+ New brand"
CATEGORY_NAMES = {category: product_class.CATEGORY_NAME
                  for category, product_class in ProductFactory.CATEGORIES.items()}


class InventoryGui:
    """One page per menu option. Streamlit re-runs the whole script after every
    click, so the Inventory and the order being built are kept in session_state.

    The Streamlit module is passed in as `ui` (dependency injection), so the tests
    can use a fake one instead of a browser. AGGREGATION: the InventoryStore is
    created outside (by StoreFactory, or by the tests) and passed in.
    """

    PAGES = ("Products", "Restock list", "Add product", "Update stock & PAR", "Remove product",
             "Search product", "Create order", "Import from CSV")

    def __init__(self, ui, store: InventoryStore | None = None):
        self.__ui = ui
        state = ui.session_state
        if "inventory" not in state:
            warning = ""
            if store is None:
                store, warning = StoreFactory.from_env(INVENTORY_PATH)
            inventory = Inventory()
            message = store.load(inventory)
            state["store"] = store
            state["inventory"] = inventory
            state["order_lines"] = []          # (product_id, quantity) pairs
            state["unsaved"] = False
            state["flash"] = "\n".join(text for text in (warning, message) if text)
        self.__store: InventoryStore = state["store"]
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
        if product is None:
            return product_id
        return f"{product_id} - {product.get_brand().get_name()} {product.get_name()}"

    def __product_ids(self) -> list[str]:
        return [product.get_product_id() for product in self.__inventory.get_products()]

    # ---------- page layout ----------

    def run(self) -> None:
        ui = self.__ui
        ui.set_page_config(page_title="Sephora Inventory Tracker", layout="wide")
        ui.title("Sephora Inventory Tracker")
        flash = ui.session_state.pop("flash", "")
        if flash:
            ui.info(flash)

        page = ui.sidebar.radio("Menu", self.PAGES, key="page")
        ui.sidebar.divider()
        ui.sidebar.caption(f"Storage: {self.__store.name}")
        if ui.session_state.get("unsaved"):
            ui.sidebar.warning("You have unsaved changes.")
        if ui.sidebar.button("Save inventory", key="save"):
            saved, message = self.__store.save(self.__inventory)   # JSON or MongoDB: same call
            if saved:
                ui.session_state["unsaved"] = False
                self.__finish(message, changed=False)
            ui.sidebar.error(message)

        {"Products": self.__products, "Restock list": self.__restock, "Add product": self.__add,
         "Update stock & PAR": self.__update_stock,
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
        categories = first.multiselect("Category", list(CATEGORY_NAMES), key="filter_category",
                                       format_func=CATEGORY_NAMES.get, placeholder="All categories")
        brand_names = sorted(brand.get_name() for brand in self.__inventory.get_brands().values())
        brands = second.multiselect("Brand", brand_names, key="filter_brand", placeholder="All brands")
        below_only = ui.checkbox("Only products below PAR", key="filter_below_par")
        shown = [product for product in products
                 if (not categories or product.CATEGORY in categories)
                 and (not brands or product.get_brand().get_name() in brands)
                 and (not below_only or product.is_below_par())]

        first, second, third = ui.columns(3)
        first.metric("Products", len(shown))
        second.metric("Stock value", f"${sum(p.get_price() * p.get_stock() for p in shown):,.2f}")
        third.metric("Below PAR", sum(product.is_below_par() for product in shown))
        if shown:
            ui.dataframe([self.__row(product) for product in shown], hide_index=True)
        else:
            ui.info("No products match these filters.")

    @staticmethod
    def __row(product: Product) -> dict:
        """One table row. POLYMORPHISM: each category gives its own detail label and value."""
        return {"ID": product.get_product_id(), "Brand": product.get_brand().get_name(),
                "Name": product.get_name(), "Category": product.CATEGORY_NAME,
                "Detail": f"{product.get_detail_label()}: {product.get_detail_text()}",
                "Price": f"${product.get_price():.2f}", "Stock": product.get_stock(),
                "PAR": product.get_par_level(),
                "Status": (f"Below PAR: order {product.get_restock_quantity()}"
                           if product.is_below_par() else "OK")}

    # ---------- restock list ----------

    def __restock(self) -> None:
        """Every product below PAR, grouped by brand, with how many to order."""
        ui = self.__ui
        ui.subheader("Restock list")
        ui.caption("Products whose stock is below their PAR level. Ordering the amount shown "
                   "brings each one back up to PAR.")
        products = self.__inventory.get_products_below_par()     # already sorted by brand
        if not products:
            ui.success("Every product is at or above PAR. Nothing to restock.")
            return
        first, second, third = ui.columns(3)
        first.metric("Products to restock", len(products))
        second.metric("Units to order", sum(product.get_restock_quantity() for product in products))
        third.metric("Value at retail price", f"${self.__restock_value(products):,.2f}")

        by_brand: dict[str, list[Product]] = {}
        for product in products:
            by_brand.setdefault(product.get_brand().get_name(), []).append(product)
        for brand_name, brand_products in by_brand.items():
            ui.markdown(f"**{brand_name}** ({len(brand_products)} products, "
                        f"${self.__restock_value(brand_products):,.2f})")
            ui.dataframe([self.__restock_row(product) for product in brand_products], hide_index=True)

        ui.download_button("Download restock list (CSV)", self.__restock_csv(products),
                           file_name="restock_list.csv", mime="text/csv", key="restock_download")
        sure = ui.checkbox("The order has arrived: set every product above back to its PAR level",
                           key="restock_sure")
        if ui.button("Mark as restocked", key="restock_button", disabled=not sure):
            for product in products:
                product.update_stock(product.get_par_level())
            self.__finish(f"{len(products)} products restocked to PAR.")

    @staticmethod
    def __restock_value(products: list[Product]) -> float:
        return sum(product.get_restock_quantity() * product.get_price() for product in products)

    @staticmethod
    def __restock_row(product: Product) -> dict:
        return {"ID": product.get_product_id(), "Name": product.get_name(),
                "Category": product.CATEGORY_NAME,
                "Detail": f"{product.get_detail_label()}: {product.get_detail_text()}",
                "Stock": product.get_stock(), "PAR": product.get_par_level(),
                "Order": product.get_restock_quantity()}

    @staticmethod
    def __restock_csv(products: list[Product]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["brand", "product_id", "name", "category", "detail", "stock", "par", "order"])
        for product in products:
            writer.writerow([product.get_brand().get_name(), product.get_product_id(), product.get_name(),
                             product.CATEGORY_NAME, product.get_detail_text(), product.get_stock(),
                             product.get_par_level(), product.get_restock_quantity()])
        return output.getvalue()

    # ---------- 2. add product ----------

    def __choose_brand(self) -> Brand | None:
        """Pick an existing brand (its products share one Brand object) or type a new one."""
        ui = self.__ui
        brands = self.__inventory.get_brands()
        options = sorted(brand.get_name() for brand in brands.values()) + [NEW_BRAND]
        choice = ui.selectbox("Brand", options, key="add_brand")
        if choice != NEW_BRAND:
            return brands[choice.lower()]
        name = ui.text_input("Brand name", key="add_brand_name").strip()
        country = ui.text_input("Brand country (optional)", key="add_brand_country").strip()
        if not name:
            return None
        return brands.get(name.lower()) or Brand(name, country)   # reuse it if it already exists

    def __detail_input(self, category: str):
        """The category's own extra detail: skin type, shade, hair type or size."""
        ui = self.__ui
        if category == "face":
            return ui.selectbox("Skin type", FaceProduct.SKIN_TYPES, key="add_skin")
        if category == "hair":
            return ui.selectbox("Hair type", HairProduct.HAIR_TYPES, key="add_hair")
        if category == "body":
            return ui.number_input("Size (ml)", min_value=1.0, value=100.0, step=10.0, key="add_size")
        return ui.text_input("Shade", key="add_shade", placeholder="e.g. 240 or Ruby Woo").strip()

    def __add(self) -> None:
        ui = self.__ui
        ui.subheader("Add new product")
        category = ui.radio("Category", list(CATEGORY_NAMES), key="add_category",
                            format_func=CATEGORY_NAMES.get, horizontal=True)
        product_id = ui.text_input("Product ID", key="add_id", placeholder="e.g. F010").strip()
        name = ui.text_input("Product name", key="add_name").strip()
        brand = self.__choose_brand()
        price = ui.number_input("Price ($)", min_value=0.01, value=10.00, step=1.00, key="add_price")
        stock = int(ui.number_input("Stock quantity", min_value=0, value=0, step=1, key="add_stock"))
        par_level = int(ui.number_input("PAR level (stock to keep on the shelf)", min_value=0,
                                        value=DEFAULT_PAR_LEVEL, step=1, key="add_par"))
        detail = self.__detail_input(category)
        if not ui.button("Add product", key="add_button", type="primary"):
            return
        if not product_id or not name:
            ui.error("Product ID and name cannot be empty.")
        elif self.__inventory.find_product(product_id) is not None:
            ui.error("A product with this ID already exists.")
        elif brand is None:
            ui.error("Fill in the brand name.")
        else:
            try:
                product = ProductFactory.create(category, product_id, name, price, stock, brand,
                                                detail, par_level)
            except ValueError as error:          # the product classes explain what is wrong
                ui.error(str(error))
                return
            self.__inventory.add_product(product)
            self.__finish(f"{brand.get_name()} {name} added successfully.")

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
        ui.subheader("Update stock & PAR")
        product = self.__pick_product("stock_product")
        if product is None:
            return
        product_id = product.get_product_id()
        ui.write(f"Current stock: **{product.get_stock()}** (PAR {product.get_par_level()})")
        first, second = ui.columns(2)
        new_stock = int(first.number_input("New stock quantity", min_value=0, value=product.get_stock(),
                                           step=1, key=f"stock_{product_id}"))
        new_par = int(second.number_input("PAR level", min_value=0, value=product.get_par_level(),
                                          step=1, key=f"par_{product_id}"))
        if ui.button("Update", key="stock_button", type="primary"):
            product.update_stock(new_stock)
            product.set_par_level(new_par)
            message = f"{product.get_name()}: stock {new_stock}, PAR {new_par}."
            if product.is_below_par():
                message += f" Still below PAR: order {product.get_restock_quantity()}."
            self.__finish(message)

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
        text = ui.text_input("Product ID, name or brand", key="search_text",
                             placeholder="e.g. F001, foundation or Dior").strip()
        if not text:
            return
        product = self.__inventory.find_product(text)
        matches = [product] if product is not None else [
            p for p in self.__inventory.get_products()
            if text.lower() in p.get_name().lower() or text.lower() in p.get_brand().get_name().lower()]
        if not matches:
            ui.warning("Product not found.")
            return
        if len(matches) > 1:
            ui.success(f"{len(matches)} products found")
            ui.dataframe([self.__row(match) for match in matches], hide_index=True)
            return
        product = matches[0]
        brand = product.get_brand()
        details = [("Name", product.get_name()),
                   ("Brand", brand.get_name() + (f" ({brand.get_country()})" if brand.get_country() else "")),
                   ("Category", product.CATEGORY_NAME),
                   (product.get_detail_label(), product.get_detail_text()),
                   ("Price", f"${product.get_price():.2f}"),
                   ("Stock", f"{product.get_stock()} (PAR {product.get_par_level()})"),
                   ("Restock", f"Below PAR: order {product.get_restock_quantity()}"
                    if product.is_below_par() else "At or above PAR"),
                   ("Tip", product.get_care_tip())]       # POLYMORPHISM: each category's own tip
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
        ui.caption(f"Columns: {', '.join(CSV_COLUMNS)}, and optionally par. The detail is the skin "
                   "type, shade, hair type or size in ml. Bad rows are skipped and reported; "
                   "good rows still load.")
        uploaded = ui.file_uploader("CSV file (leave empty to use products.csv)", type=["csv"],
                                    key="csv_file")
        if not ui.button("Import products", key="csv_button", type="primary"):
            return
        if uploaded is None:
            messages = self.__captured(load_products, PRODUCTS_CSV_PATH, self.__inventory)
        else:
            with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as file:
                file.write(uploaded.getvalue())
            try:
                messages = self.__captured(load_products, file.name, self.__inventory)
            finally:
                os.remove(file.name)
        self.__finish(messages)


if __name__ == "__main__":
    import streamlit
    InventoryGui(streamlit).run()
