from discount_strategy import DiscountStrategy

STUDENT_PERCENTAGE = 5   # students get 5% off


class StudentDiscount(DiscountStrategy):
    """A new strategy added in its own file. Order did not need to change (Open/Closed Principle)."""

    def apply(self, total: float) -> float:
        return total * (1 - STUDENT_PERCENTAGE / 100)