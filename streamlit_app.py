"""
Streamlit web GUI for the Sephora Inventory Tracker (5 stores, staff logins).

Run with:  streamlit run streamlit_app.py

Employees log in to their own store; the master login can open every store, see
an overview of all of them and manage staff logins. The inventory pages use the
same classes as the terminal menu: Inventory, ProductFactory (Face, Makeup, Hair
and Body products), Brand, Order, the DiscountStrategy classes and file_handler.py.
StoreFactory decides whether data is kept in JSON files or MongoDB (see .env.example).
"""
from __future__ import annotations

import csv
import io
import os
import tempfile
from contextlib import redirect_stdout

from account_gui import AccountGui
from account_manager import AccountManager
from brand import Brand
from branch import Branch, BRANCH_NAMES
from daily_stock_record import DailyStockRecord
from face_product import FaceProduct
from file_handler import load_products, CSV_COLUMNS
from hair_product import HairProduct
from inventory import Inventory
from main import DISCOUNT_OPTIONS
from order import Order
from product import Product, DEFAULT_PAR_LEVEL
from product_factory import ProductFactory
from store_factory import StoreFactory

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_CSV_PATH = os.path.join(APP_DIR, "products.csv")
NEW_BRAND = "+ New brand"
ALL_STORES = "All stores"
CATEGORY_NAMES = {category: product_class.CATEGORY_NAME
                  for category, product_class in ProductFactory.CATEGORIES.items()}


class InventoryGui:
    """One page per menu option, for the store the user is working in.

    Streamlit re-runs the whole script after every click, so the loaded stores,
    the logged-in user and the order being built are kept in session_state.
    The Streamlit module is passed in as `ui` (dependency injection), so the tests
    can use a fake one instead of a browser. AGGREGATION: the StoreFactory is
    created outside (from .env, or by the tests) and passed in.
    COMPOSITION: InventoryGui creates the AccountGui it uses for the login screens.
    """

    PAGES = ("Products", "Restock list", "Daily stock", "Add product", "Update stock & PAR", "Remove product",
             "Search product", "Create order", "Import from CSV")
    MASTER_PAGES = ("Overview", "Manage staff")

    def __init__(self, ui, factory: StoreFactory | None = None):
        self.__ui = ui
        state = ui.session_state
        if "factory" not in state:
            warning = ""
            if factory is None:
                factory, warning = StoreFactory.from_env(APP_DIR)
            state["factory"] = factory
            state["flash"] = warning
            try:
                state["accounts"] = AccountManager(factory.account_store())
            except (OSError, KeyError, TypeError, ValueError) as error:
                state["accounts"] = None           # never offer "first-time setup" over unreadable accounts
                state["accounts_error"] = str(error)
            self.__reset_work(state)
        self.__factory: StoreFactory = state["factory"]
        self.__accounts: AccountManager | None = state["accounts"]
        self.__branch: Branch | None = None       # the store being worked on in this run
        self.__inventory: Inventory | None = None

    @staticmethod
    def __reset_work(state) -> None:
        """Forget loaded stores, unsaved changes and orders (at start and on log out)."""
        state["branches"] = {}                     # store name -> Branch, loaded when first opened
        state["unsaved"] = set()                   # names of stores with unsaved changes
        state["order_lines"] = {}                  # store name -> [(product_id, quantity)]

    @staticmethod
    def __captured(function, *args) -> str:
        """Run a file_handler function and return what it printed, to show on screen."""
        output = io.StringIO()
        with redirect_stdout(output):
            function(*args)
        return output.getvalue().strip()

    def __finish(self, message: str, changed: bool = True) -> None:
        """Remember a message, mark the store as having unsaved changes and redraw the page."""
        self.__ui.session_state["flash"] = message
        if changed and self.__branch is not None:
            self.__ui.session_state["unsaved"].add(self.__branch.get_name())
        self.__ui.rerun()

    def __open_branch(self, name: str) -> Branch:
        """The store's Branch, loaded from JSON or MongoDB the first time it is opened."""
        branches = self.__ui.session_state["branches"]
        if name not in branches:
            branches[name] = Branch(name, self.__factory.inventory_store(name))
            self.__ui.info(branches[name].get_load_message())
        return branches[name]

    # ---------- page layout ----------

    def run(self) -> None:
        ui = self.__ui
        state = ui.session_state
        ui.set_page_config(page_title="Sephora Inventory Tracker", layout="wide")
        ui.title("Sephora Inventory Tracker")
        flash = state.pop("flash", "")
        if flash:
            ui.info(flash)
        if self.__accounts is None:
            ui.error(f"The staff accounts could not be read, so nobody can log in: "
                     f"{state.get('accounts_error')}")
            return
        account_gui = AccountGui(ui, self.__accounts)
        if not self.__accounts.has_master():
            account_gui.setup()
            return
        user = state.get("user")
        if user is None:
            account_gui.login()
            return

        ui.sidebar.write(f"Logged in: **{user.get_username()}**")
        ui.sidebar.caption(user.describe())
        allowed = [name for name in BRANCH_NAMES if user.can_access(name)]   # POLYMORPHISM
        if user.is_master():                       # POLYMORPHISM: each account answers for itself
            store = ui.sidebar.selectbox("Store", [ALL_STORES] + allowed, key="branch")
        else:
            store = allowed[0]
            ui.sidebar.write(f"Store: **{store}**")
        if store == ALL_STORES:
            page = ui.sidebar.radio("Menu", self.MASTER_PAGES, key="master_page")
        else:
            page = ui.sidebar.radio("Menu", self.PAGES, key="page")
            self.__branch = self.__open_branch(store)
            self.__inventory = self.__branch.get_inventory()
        ui.sidebar.divider()
        self.__sidebar_save(store)
        if ui.sidebar.button("Log out", key="logout"):
            state.pop("user", None)        # the store and menu choices reset by themselves
            self.__reset_work(state)
            state["flash"] = "Logged out."
            ui.rerun()

        if store == ALL_STORES:
            {"Overview": self.__overview, "Manage staff": account_gui.manage_staff}[page]()
            return
        ui.header(store)
        {"Products": self.__products, "Restock list": self.__restock, "Daily stock": self.__daily,
         "Add product": self.__add,
         "Update stock & PAR": self.__update_stock,
         "Remove product": self.__remove, "Search product": self.__search,
         "Create order": self.__order, "Import from CSV": self.__import}[page]()

    def __sidebar_save(self, store: str) -> None:
        """Save this store (or, in the overview, every store that has been opened).
        The button is always available: a store that started from its sample file
        has no changes yet but still needs saving once to get its own copy."""
        ui = self.__ui
        unsaved = ui.session_state["unsaved"]
        to_save = sorted(ui.session_state["branches"]) if store == ALL_STORES else [store]
        if self.__branch is not None:
            ui.sidebar.caption(f"Storage: {self.__branch.get_storage_name()}")
        if unsaved:
            ui.sidebar.warning("Unsaved changes in: " + ", ".join(sorted(unsaved)) +
                               ". Logging out discards them.")
        label = "Save all stores" if store == ALL_STORES else "Save inventory"
        if not ui.sidebar.button(label, key="save"):
            return
        messages, failed = [], False
        for name in to_save:
            saved, message = ui.session_state["branches"][name].save()   # JSON or MongoDB: same call
            messages.append(message)
            if saved:
                unsaved.discard(name)
            failed = failed or not saved
        if failed:
            ui.sidebar.error("\n".join(messages))
            return
        ui.session_state["flash"] = "\n".join(messages)
        ui.rerun()

    # ---------- master: all stores ----------

    def __overview(self) -> None:
        """Every store side by side, and one restock list for all of them."""
        ui = self.__ui
        ui.subheader("All stores")
        branches = [self.__open_branch(name) for name in BRANCH_NAMES]
        rows = []
        for branch in branches:
            products = branch.get_inventory().get_products()
            below = branch.get_inventory().get_products_below_par()
            rows.append({"Store": branch.get_name(), "Products": len(products),
                         "Units in stock": sum(p.get_stock() for p in products),
                         "Stock value": f"${sum(p.get_price() * p.get_stock() for p in products):,.2f}",
                         "Below PAR": len(below),
                         "Units to order": sum(p.get_restock_quantity() for p in below)})
        ui.dataframe(rows, hide_index=True)
        ui.download_button("Download restock list for all stores (CSV)",
                           self.__restock_csv([(b.get_name(), p) for b in branches
                                               for p in b.get_inventory().get_products_below_par()]),
                           file_name="restock_all_stores.csv", mime="text/csv", key="restock_all_download")

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

        store = self.__branch.get_name()
        ui.download_button("Download restock list (CSV)",
                           self.__restock_csv([(store, product) for product in products]),
                           file_name=f"restock_{Branch.key(store)}.csv", mime="text/csv", key="restock_download")
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
    def __restock_csv(lines: list[tuple[str, Product]]) -> str:
        """A CSV of (store name, product) pairs, with how many of each to order."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["store", "brand", "product_id", "name", "category", "detail",
                         "stock", "par", "order"])
        for store, product in lines:
            writer.writerow([store, product.get_brand().get_name(), product.get_product_id(),
                             product.get_name(), product.CATEGORY_NAME, product.get_detail_text(),
                             product.get_stock(), product.get_par_level(), product.get_restock_quantity()])
        return output.getvalue()

    # ---------- daily leftover stock ----------

    def __daily(self) -> None:
        """Record each day's closing (leftover) stock, and look back at any recorded day."""
        ui = self.__ui
        store = self.__branch.get_name()
        history = self.__factory.history_store(store)
        ui.subheader("Daily leftover stock")
        try:
            records = history.load()
        except OSError as error:
            ui.error(str(error))
            return

        ui.markdown("**Record closing stock**")
        ui.caption("Takes a snapshot of every product's stock as it is now. Do it at closing time; "
                   "recording a day again replaces that day's record.")
        today = DailyStockRecord.today()
        day = ui.date_input("Day", value=today, max_value=today, format="DD-MM-YYYY", key="daily_day")
        allowed = True
        if any(record.get_day() == day for record in records):
            allowed = ui.checkbox(f"Replace the record already saved for {day:%d-%m-%Y}",
                                  key=f"daily_replace_{day}")
        if ui.button("Record closing stock", key="daily_record", type="primary", disabled=not allowed):
            user = ui.session_state["user"].get_username()
            try:
                record = DailyStockRecord.from_inventory(store, day, self.__inventory, user)
            except ValueError as error:
                ui.error(str(error))
                return
            if not history.save(record):
                ui.error("The daily stock could not be saved. Please try again.")
                return
            self.__finish(f"Closing stock for {day:%d-%m-%Y} recorded: {record.total_units()} units.",
                          changed=False)

        if not records:
            ui.info("No days recorded yet.")
            return
        ui.markdown("**View by day**")
        days = [record.get_day() for record in records]          # oldest first
        chosen = ui.selectbox("Day", list(reversed(days)), key="daily_view",
                              format_func=lambda d: d.strftime("%a %d-%m-%Y"))
        index = days.index(chosen)
        record = records[index]
        previous = records[index - 1] if index > 0 else None
        rows = record.compare_with(previous)

        first, second, third = ui.columns(3)
        first.metric("Units left", record.total_units())
        second.metric("Below PAR", record.below_par_count())
        third.metric("Change since previous day",
                     "-" if previous is None else f"{record.total_units() - previous.total_units():+d}")
        compared = ("the first recorded day" if previous is None
                    else f"compared with {previous.get_day():%d-%m-%Y}")
        ui.caption(f"Recorded by {record.get_recorded_by()} at {record.get_recorded_at()[11:16]}, "
                   f"{compared}.")
        ui.dataframe([{"ID": row["id"], "Brand": row["brand"], "Name": row["name"],
                       "Leftover": row["stock"], "PAR": row["par"],
                       "Status": "Below PAR" if row["stock"] < row["par"] else "OK",
                       "Change": "new" if row["change"] is None else f"{row['change']:+d}"}
                      for row in rows], hide_index=True)
        ui.download_button(f"Download {chosen:%d-%m-%Y} (CSV)", self.__daily_csv(record, rows),
                           file_name=f"stock_{Branch.key(store)}_{chosen.isoformat()}.csv",
                           mime="text/csv", key="daily_download")
        self.__daily_chart(records)

    def __daily_chart(self, records: list[DailyStockRecord]) -> None:
        """Leftover stock over the recorded days: all products together, or one product with its PAR."""
        ui = self.__ui
        names = {}
        for record in records:
            for count in record.get_counts():
                names[count["id"]] = f"{count['id']} - {count['brand']} {count['name']}"
        options = ["All products"] + sorted(names)
        chosen = ui.selectbox("Chart", options, key="daily_chart",
                              format_func=lambda option: names.get(option, option))
        days = [record.get_day().strftime("%d-%m") for record in records]
        if chosen == "All products":
            ui.line_chart({"Day": days, "Units left": [record.total_units() for record in records]},
                          x="Day", y="Units left")
            return
        stock, par = [], []
        for record in records:
            count = next((c for c in record.get_counts() if c["id"] == chosen), None)
            stock.append(None if count is None else count["stock"])
            par.append(None if count is None else count["par"])
        ui.line_chart({"Day": days, "Leftover": stock, "PAR": par}, x="Day", y=["Leftover", "PAR"])

    @staticmethod
    def __daily_csv(record: DailyStockRecord, rows: list[dict]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["store", "date", "product_id", "brand", "name", "leftover", "par", "change"])
        for row in rows:
            writer.writerow([record.get_store(), record.get_day().isoformat(), row["id"], row["brand"],
                             row["name"], row["stock"], row["par"],
                             "" if row["change"] is None else row["change"]])
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
        """Choose a product in three steps: category, then brand, then the product itself.
        Each list only shows what is in this store, so there is nothing to type."""
        ui = self.__ui
        products = self.__inventory.get_products()
        if not products:
            ui.info("Inventory is empty.")
            return None
        categories = [category for category in CATEGORY_NAMES
                      if any(product.CATEGORY == category for product in products)]
        first, second, third = ui.columns(3)
        category = first.selectbox("Category", categories, key=f"{key}_category",
                                   format_func=CATEGORY_NAMES.get)
        in_category = [product for product in products if product.CATEGORY == category]
        brands = sorted({product.get_brand().get_name() for product in in_category}, key=str.lower)
        # The keys include the earlier choices, so each list remembers its own selection.
        brand = second.selectbox("Brand", brands, key=f"{key}_brand_{category}")
        choices = sorted((product for product in in_category if product.get_brand().get_name() == brand),
                         key=lambda product: product.get_name().lower())
        names = {product.get_product_id(): f"{product.get_name()} ({product.get_detail_text()})"
                 for product in choices}
        chosen = third.selectbox("Product", list(names), key=f"{key}_product_{category}_{brand}",
                                 format_func=names.get)
        return self.__inventory.find_product(chosen)

    def __update_stock(self) -> None:
        ui = self.__ui
        ui.subheader("Update stock & PAR")
        product = self.__pick_product("stock")
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
        product = self.__pick_product("remove")
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
        product = self.__pick_product("search")
        if product is None:
            return
        self.__show_details(product)
        with ui.expander("Or search by ID, name or brand"):
            text = ui.text_input("Product ID, name or brand", key="search_text",
                                 placeholder="e.g. F001, foundation or Dior").strip()
            if not text:
                return
            found = self.__inventory.find_product(text)
            matches = [found] if found is not None else [
                p for p in self.__inventory.get_products()
                if text.lower() in p.get_name().lower() or text.lower() in p.get_brand().get_name().lower()]
            if not matches:
                ui.warning("Product not found.")
            else:
                ui.success(f"{len(matches)} product(s) found")
                ui.dataframe([self.__row(match) for match in matches], hide_index=True)

    def __show_details(self, product: Product) -> None:
        brand = product.get_brand()
        details = [("ID", product.get_product_id()),
                   ("Name", product.get_name()),
                   ("Brand", brand.get_name() + (f" ({brand.get_country()})" if brand.get_country() else "")),
                   ("Category", product.CATEGORY_NAME),
                   (product.get_detail_label(), product.get_detail_text()),
                   ("Price", f"${product.get_price():.2f}"),
                   ("Stock", f"{product.get_stock()} (PAR {product.get_par_level()})"),
                   ("Restock", f"Below PAR: order {product.get_restock_quantity()}"
                    if product.is_below_par() else "At or above PAR"),
                   ("Tip", product.get_care_tip())]       # POLYMORPHISM: each category's own tip
        self.__ui.dataframe([{"Detail": label, "Value": value} for label, value in details], hide_index=True)

    # ---------- 6. create order ----------

    def __order(self) -> None:
        ui = self.__ui
        all_lines = ui.session_state["order_lines"]
        store = self.__branch.get_name()             # each store builds its own order
        ui.subheader("Create order")
        order_id = ui.text_input("Order ID", value="O001", key="order_id").strip() or "O001"
        product = self.__pick_product("order")          # category, then brand, then product
        if product is not None:
            first, second = ui.columns(2)
            quantity = int(first.number_input("Quantity", min_value=1, value=1, step=1, key="order_qty"))
            second.metric("In stock", product.get_stock())
            if ui.button("Add to order", key="order_add"):
                all_lines[store] = all_lines.get(store, []) + [(product.get_product_id(), quantity)]

        # COMPOSITION: the Order creates its own OrderLines from the chosen products.
        labels = [label for label, _ in DISCOUNT_OPTIONS.values()]
        label = ui.selectbox("Discount", labels, key="order_discount")
        discount = next(strategy for name, strategy in DISCOUNT_OPTIONS.values() if name == label)
        order = Order(order_id, discount)            # STRATEGY: the Order just calls apply()
        for product_id, quantity in all_lines.get(store, []):
            product = self.__inventory.find_product(product_id)
            if product is not None:                  # skip products removed since
                order.add_order_line(product, quantity)

        lines = order.get_order_lines()
        if not lines:
            ui.info("No items yet. Choose a product and click Add to order.")
            return
        ui.dataframe([{"ID": line.get_product().get_product_id(),
                       "Brand": line.get_product().get_brand().get_name(),
                       "Name": line.get_product().get_name(),
                       "Qty": line.get_quantity(), "Unit price": f"${line.get_product().get_price():.2f}",
                       "Subtotal": f"${line.calculate_subtotal():.2f}"} for line in lines], hide_index=True)
        first, second, third = ui.columns(3)
        first.metric("Subtotal", f"${order.calculate_subtotal():.2f}")
        second.metric("Discount", type(order.get_discount()).__name__)
        third.metric("Total", f"${order.calculate_total():.2f}")
        problems = order.get_stock_problems()
        for problem in problems:
            ui.warning(problem)
        first, second = ui.columns(2)
        if first.button("Confirm order", key="order_confirm", type="primary", disabled=bool(problems)):
            try:
                order.confirm()                      # takes the quantities off the stock
            except ValueError as error:
                ui.error(str(error))
                return
            all_lines[store] = []
            units = sum(line.get_quantity() for line in lines)
            message = f"Order {order_id} confirmed: {units} item(s) taken off the stock."
            below = sorted({line.get_product().get_name() for line in lines
                            if line.get_product().is_below_par()})
            if below:
                message += " Now below PAR (on the restock list): " + ", ".join(below) + "."
            self.__finish(message)                   # the store now has unsaved changes
        if second.button("Clear order", key="order_clear"):
            all_lines[store] = []
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
