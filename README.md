# Sephora Inventory Tracker

An inventory tracker for a Sephora store, built on my INF1103 Week 11 lab
(Factory pattern, Strategy pattern, CSV import and error handling). It runs as
a Streamlit web app, and the original terminal menu still works.

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

## Pages

| Page | What it does | Terminal menu option |
|---|---|---|
| Products | Table with stock, PAR and status; filter by category, brand or below PAR | 1 |
| Restock list | Products below PAR, grouped by brand, with the amount to order | 8 |
| Add product | Pick a category, brand (existing or new), PAR level and the category's detail | 2 |
| Update stock & PAR | Set a new stock level and PAR level | 4 |
| Remove product | Needs a tick to confirm | 3 |
| Search product | By ID, name or brand; shows the detail, PAR and a tip for staff | 5 |
| Create order | Add lines, pick a discount, see subtotal and total | 6 |
| Import from CSV | Upload a file or use `products.csv` | 7 |
| **Save inventory** (sidebar) | Writes to `inventory.json` or MongoDB | 9 |

Changes are kept while the browser tab is open. Click **Save inventory** to keep
them; the sidebar warns you when there are unsaved changes.

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Your browser opens at http://localhost:8501. For the terminal version, run `python3 main.py`.

## Storing the inventory in MongoDB (optional)

By default the products are kept in `inventory.json`. To keep them in MongoDB Atlas instead:

1. In Atlas, create a free cluster (or use an existing one), a database user, and
   allow your IP address under **Network Access**.
2. Copy `.env.example` to `.env` and put your connection string in `MONGODB_URI`.
   Write each line as `KEY=value`, with no spaces or quotes.
3. Run the app. The sidebar shows **Storage: MongoDB (sephora_inventory)**.

The first time, the database is empty, so the app starts from `inventory.json`.
Click **Save inventory** to copy the products into MongoDB. After that they are
loaded from the `products` collection, one document per product.

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
| `test_gui.py` | every page, with a fake Streamlit (`fake_streamlit.py`) |
| `test_storage.py` | JSON and MongoDB storage, with a fake database (`fake_mongo.py`) |

Every test works on a temporary copy of `inventory.json`, and none connects to the real database.

## Project structure

```
streamlit_app.py      the GUI (InventoryGui class, one method per page)
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
store_factory.py      Factory pattern: picks JSON or MongoDB from .env
tests/                unit tests
```
