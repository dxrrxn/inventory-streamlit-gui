# Sephora Inventory Tracker

An inventory tracker for five Sephora stores (Sengkang, Punggol, Hougang, Kovan
and Serangoon), built on my INF1103 Week 11 lab (Factory pattern, Strategy
pattern, CSV import and error handling). It runs as a Streamlit web app with
staff logins.

## Stores and logins

- Each store has **its own products, stock and PAR levels**. A change in Kovan
  doesn't affect Punggol.
- **Employees** log in to the one store they work at.
- The **master** login can open every store, see an **Overview** of all five
  (products, stock value, products below PAR, units to order), download one
  restock list for all stores, and **Manage staff**: add employees (each tied to
  one store), reset passwords and remove logins.
- **First run:** the app asks you to create the master account. After that it
  shows the login page.
- Passwords are never stored. Only a salted PBKDF2-SHA256 hash is kept, and a
  wrong username or password gets the same message.
- A store that has never been saved starts from its own sample file in
  `sample_data/` (different products and stock in each store); click
  **Save inventory** to keep its own copy.

Products belong to one of four categories, and each category has its own extra detail:

| Category | Class | Extra detail |
|---|---|---|
| Face & skincare | `FaceProduct` | skin type (All, Normal, Dry, Oily, Combination, Sensitive) |
| Makeup | `MakeupProduct` | shade, e.g. `240` or `Ruby Woo` |
| Hair | `HairProduct` | hair type (All, Straight, Wavy, Curly, Coily) |
| Body & fragrance | `BodyProduct` | size in ml |

Every product also has a **brand** (e.g. Fenty Beauty, Dior). Products of the
same brand share one `Brand` object.

## PAR levels and the restock list

Each product has a **PAR level**: the stock the store wants to keep on the shelf
(10 if none is given). When the stock falls below PAR, the product is marked
**Below PAR** and goes on the **restock list**, which shows how many to order to
get back to PAR:

```
order = PAR - stock      (never less than 0)
```

The restock list is grouped by brand, so each brand's order can be placed in one
go. It can be downloaded as a CSV file, and **Mark as restocked** sets every listed
product back to its PAR level when the delivery arrives.

## Daily leftover stock

At closing time, staff open **Daily stock** and click **Record closing stock**.
This saves a snapshot of every product's stock and PAR level for that day; later
changes don't alter it. A past day can be recorded too, and recording a day again
replaces it (after a confirming tick).

Under **View by day**, pick any recorded day to see each product's leftover stock,
whether it was below PAR, and the change since the previous recorded day ("new"
for a product that wasn't stocked then). Each day can be downloaded as a CSV file,
and a chart shows the leftover stock over time, for all products together or for
one product against its PAR level. Each store has its own history.

## Pages

| Page | What it does | Terminal menu option |
|---|---|---|
| Products | Table with stock, PAR and status; filter by category, brand or below PAR | 1 |
| Restock list | Products below PAR, grouped by brand, with the amount to order | 8 |
| Daily stock | Record the closing stock; view any day, the change since the day before, and a chart | - |
| Add product | Pick a category, brand (existing or new), PAR level and the category's detail | 2 |
| Update stock & PAR | Set a new stock level and PAR level | 4 |
| Remove product | Needs a tick to confirm | 3 |
| Search product | By ID, name or brand; shows the detail, PAR and a tip for staff | 5 |
| Create order | Add lines, pick a discount, see subtotal and total | 6 |
| Import from CSV | Upload a file or use `products.csv` | 7 |
| **Save inventory** (sidebar) | Saves this store (the master's Overview has **Save all stores**) | 9 |

Changes are kept while the browser tab is open. Click **Save inventory** to keep
them; the sidebar lists the stores with unsaved changes, and logging out discards them.

The terminal menu (`python3 main.py`) is the original single-store lab version:
it has no logins and works on `inventory.json` directly.

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Your browser opens at http://localhost:8501. For the terminal version, run `python3 main.py`.

## Where the data is kept

By default everything is in JSON files next to the app (none of them are committed to Git):

| File | What's in it |
|---|---|
| `stores/sengkang.json`, `stores/kovan.json`, ... | each store's products, once saved |
| `stores/sengkang_history.json`, ... | each store's daily leftover stock |
| `accounts.json` | the logins, with hashed passwords |

## Storing the data in MongoDB (optional)

To keep the stores and logins in MongoDB Atlas instead:

1. In Atlas, create a free cluster (or use an existing one), a database user, and
   allow your IP address under **Network Access**.
2. Copy `.env.example` to `.env` and put your connection string in `MONGODB_URI`.
   Write each line as `KEY=value`, with no spaces or quotes.
3. Run the app. The sidebar shows **Storage: MongoDB (sephora_inventory)**.

Each store gets its own collections (`products_sengkang` and
`stock_history_sengkang`, and so on) and the logins go in an `accounts` collection. The first time, the database is
empty: the app asks for a master account, and each store starts from its
sample file in `sample_data/` until you save it.

If MongoDB can't be reached (wrong password, IP not allowed, no internet), the
app says why and uses `inventory.json`, so it still starts. `.env` is in
`.gitignore` and `.dockerignore`, so the password never reaches GitHub or the
Docker image.

## Running it in Docker

```bash
docker build -t sephora-inventory .
docker run --rm -p 8501:8501 --env-file .env sephora-inventory
```

Then open http://localhost:8501. The build runs the tests first. Leave out
`--env-file .env` to use `inventory.json` inside the container.

## CSV import format

```
category,product_id,name,brand,price,stock_quantity,detail,par
face,F010,Water Cream,Tatcha,98.00,12,Dry,10
body,B010,Bum Bum Cream,Sol de Janeiro,65.00,3,240,8
```

`category` is `face`, `makeup`, `hair` or `body`, and `detail` is that category's
skin type, shade, hair type or size in ml. The `par` column is optional; rows
without it get a PAR level of 10. Bad rows are reported and skipped;
the sample `products.csv` includes some on purpose.

## Tests

```bash
python3 -m unittest discover -s tests
```

| File | What it tests |
|---|---|
| `test_products.py` | the category classes, validation, polymorphism, the shared Brand and PAR levels |
| `test_factory.py` | the Factory pattern |
| `test_discounts.py` | the Strategy pattern |
| `test_error_handling.py` | input checks and CSV import |
| `test_gui.py` | every inventory page, with a fake Streamlit (`fake_streamlit.py`) |
| `test_login.py` | first-time setup, login, log out, which stores each account can open, the overview and Manage staff |
| `test_accounts.py` | password hashing, master/employee rules, saving the accounts |
| `test_daily_stock.py` | the daily snapshot, saving one record per day, and the Daily stock page |
| `test_storage.py` | JSON and MongoDB storage, with a fake database (`fake_mongo.py`) |

Every test works on a temporary copy of `inventory.json`, and none connects to the real database.

## Project structure

```
streamlit_app.py      the GUI (InventoryGui class, one method per page)
account_gui.py        the login, first-time setup and Manage staff screens
branch.py             Branch: one store and its Inventory; the five store names
account.py            abstract Account (hashed password)
employee_account.py, master_account.py   who can open which store
account_manager.py    the accounts: login, add, reset, remove
account_store.py, json_account_store.py, mongo_account_store.py   where accounts are kept
main.py               the terminal menu
product.py            abstract Product (ID, name, price, stock, PAR level, brand)
face_product.py, makeup_product.py, hair_product.py, body_product.py
brand.py              Brand (shared by its products)
product_factory.py    Factory pattern: builds the right category class
discount_strategy.py  Strategy pattern: NoDiscount, PercentageDiscount, BulkDiscount
student_discount.py   StudentDiscount
order.py, order_line.py, inventory.py
file_handler.py       JSON load/save and CSV import
inventory_store.py    InventoryStore interface (load / save)
json_inventory_store.py   keeps the products in inventory.json
mongo_inventory_store.py  keeps the products in MongoDB
daily_stock_record.py one store's leftover stock on one day
stock_history_store.py, json_stock_history_store.py, mongo_stock_history_store.py   where those are kept
store_factory.py      Factory pattern: picks JSON or MongoDB from .env, per store
tests/                unit tests
```
