# Inventory Management System: Streamlit GUI

A web GUI for my INF1103 Week 11 lab (Factory pattern, Strategy pattern, CSV
import and error handling). It does everything the terminal menu in `main.py`
does, in the browser.

The lab's classes are unchanged. `streamlit_app.py` only replaces the menu:
it calls `Inventory`, `ProductFactory`, `Order`, the `DiscountStrategy` classes
and the functions in `file_handler.py`.

## Pages

| Page | Terminal menu option |
|---|---|
| Products: table with type, shipping cost and fulfilment | 1. Display all products |
| Add product: physical or digital, existing or new supplier | 2. Add product |
| Update stock | 4. Update stock |
| Remove product (needs a tick to confirm) | 3. Remove product |
| Search product: details, shipping cost or download size, supplier | 5. Search product |
| Create order: add lines, pick a discount, see subtotal and total | 6. Create order |
| Import from CSV: upload a file or use `products.csv` | 7. Load products from CSV |
| **Save inventory** button in the sidebar | 8. Save inventory |

Changes are kept while the browser tab is open. Click **Save inventory** to
write them to `inventory.json`; the sidebar warns you when there are unsaved
changes.

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Your browser opens at http://localhost:8501. The terminal version still works
with `python3 main.py`.

## Running it in Docker

```bash
docker build -t inventory-gui .
docker run --rm -p 8501:8501 inventory-gui
```

Then open http://localhost:8501. The build runs the tests first.

## Tests

```bash
python3 -m unittest discover -s tests
```

`tests/test_gui.py` tests every page with a fake Streamlit (`tests/fake_streamlit.py`),
so no browser is needed. Each test works on a temporary copy of `inventory.json`.
The other files in `tests/` are the lab's own tests for the patterns and error handling.

## Project structure

```
streamlit_app.py      the GUI (InventoryGui class, one method per page)
main.py               the original terminal menu
product.py            abstract Product
physical_product.py   PhysicalProduct (implements CanBeShipped)
digital_product.py    DigitalProduct
can_be_shipped.py     CanBeShipped interface
product_factory.py    Factory pattern
discount_strategy.py  Strategy pattern: NoDiscount, PercentageDiscount, BulkDiscount
student_discount.py   StudentDiscount
order.py, order_line.py, supplier.py, inventory.py
file_handler.py       JSON load/save and CSV import
tests/                unit tests
```
