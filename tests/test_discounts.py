"""Tests for the Strategy pattern (Section 2)."""
import inspect
import unittest

import order as order_module
from brand import Brand
from face_product import FaceProduct
from makeup_product import MakeupProduct
from order import Order
from discount_strategy import DiscountStrategy, NoDiscount, PercentageDiscount, BulkDiscount
from student_discount import StudentDiscount


def make_order(discount: DiscountStrategy | None = None) -> Order:
    """An order whose lines add up to 250 (2 x 100 + 1 x 50)."""
    brand = Brand("Dior", "France")
    order = Order("O001", discount)
    order.add_order_line(FaceProduct("F001", "Serum", 100, 10, brand, "Dry"), 2)
    order.add_order_line(MakeupProduct("M001", "Lipstick", 50, 10, brand, "999"), 1)
    return order


class TestDiscountStrategies(unittest.TestCase):

    def test_no_discount_returns_total_unchanged(self):
        self.assertEqual(NoDiscount().apply(250), 250)

    def test_percentage_discount(self):
        self.assertAlmostEqual(PercentageDiscount(10).apply(250), 225)

    def test_bulk_discount_at_or_above_threshold(self):
        self.assertEqual(BulkDiscount(200, 20).apply(250), 230)
        self.assertEqual(BulkDiscount(200, 20).apply(200), 180)

    def test_bulk_discount_below_threshold(self):
        self.assertEqual(BulkDiscount(200, 20).apply(150), 150)

    def test_student_discount(self):
        self.assertAlmostEqual(StudentDiscount().apply(250), 237.5)

    def test_discount_strategy_cannot_be_created(self):
        with self.assertRaises(TypeError):
            DiscountStrategy()

    def test_invalid_percentage_rejected(self):
        with self.assertRaises(ValueError):
            PercentageDiscount(0)
        with self.assertRaises(ValueError):
            PercentageDiscount(150)


class TestOrderUsesStrategy(unittest.TestCase):

    def test_default_is_no_discount(self):
        order = make_order()
        self.assertIsInstance(order.get_discount(), NoDiscount)
        self.assertEqual(order.calculate_total(), 250)

    def test_bulk_then_percentage_with_set_discount(self):
        order = make_order(BulkDiscount(200, 20))
        self.assertEqual(order.calculate_total(), 230)
        order.set_discount(PercentageDiscount(10))
        self.assertAlmostEqual(order.calculate_total(), 225)

    def test_new_strategy_works_without_changing_order(self):
        order = make_order(StudentDiscount())
        self.assertAlmostEqual(order.calculate_total(), 237.5)

    def test_two_orders_can_share_one_strategy(self):
        shared = PercentageDiscount(10)
        order_1 = make_order(shared)
        order_2 = make_order(shared)
        self.assertIs(order_1.get_discount(), order_2.get_discount())
        self.assertAlmostEqual(order_1.calculate_total(), 225)
        self.assertAlmostEqual(order_2.calculate_total(), 225)

    def test_order_has_no_discount_if_elif_logic(self):
        source = inspect.getsource(order_module.Order)
        self.assertNotIn("elif", source)
        self.assertNotIn("discount_type", source)
        for name in ("PercentageDiscount", "BulkDiscount", "StudentDiscount"):
            self.assertNotIn(name, source)   # Order only knows DiscountStrategy (and the NoDiscount default)


if __name__ == "__main__":
    unittest.main()