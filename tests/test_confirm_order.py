"""Tests for confirming an order: the sold quantities come off the stock, all or nothing."""
import unittest

from brand import Brand
from face_product import FaceProduct
from makeup_product import MakeupProduct
from order import Order


class TestConfirmOrder(unittest.TestCase):

    def setUp(self):
        brand = Brand("Dior")
        self.cream = FaceProduct("F1", "Cream", 100, 5, brand, "Dry", par_level=4)
        self.lipstick = MakeupProduct("M1", "Lipstick", 50, 2, brand, "999", par_level=2)

    def test_confirm_takes_the_quantities_off_the_stock(self):
        order = Order("O001")
        order.add_order_line(self.cream, 2)
        order.add_order_line(self.lipstick, 1)
        self.assertEqual(order.get_stock_problems(), [])
        order.confirm()
        self.assertEqual((self.cream.get_stock(), self.lipstick.get_stock()), (3, 1))
        self.assertTrue(self.cream.is_below_par())            # now on the restock list

    def test_the_same_product_on_two_lines_is_added_together(self):
        order = Order("O001")
        order.add_order_line(self.cream, 3)
        order.add_order_line(self.cream, 3)                   # 6 needed, only 5 in stock
        self.assertEqual(order.get_stock_problems(), ["Only 5 Cream left, but the order needs 6."])

    def test_nothing_changes_if_any_product_is_short(self):
        order = Order("O001")
        order.add_order_line(self.cream, 1)
        order.add_order_line(self.lipstick, 3)
        with self.assertRaises(ValueError) as context:
            order.confirm()
        self.assertIn("Only 2 Lipstick left", str(context.exception))
        self.assertEqual((self.cream.get_stock(), self.lipstick.get_stock()), (5, 2))   # untouched

    def test_selling_the_last_one_leaves_zero(self):
        order = Order("O001")
        order.add_order_line(self.lipstick, 2)
        order.confirm()
        self.assertEqual(self.lipstick.get_stock(), 0)

    def test_empty_order_cannot_be_confirmed(self):
        with self.assertRaises(ValueError):
            Order("O001").confirm()


if __name__ == "__main__":
    unittest.main()
