from abc import ABC, abstractmethod


class DiscountStrategy(ABC):
    """Strategy pattern: every discount provides the same apply() method.

    Order only calls apply(). It never needs to know which discount it has.
    """

    @abstractmethod
    def apply(self, total: float) -> float:
        """Take an order total and return the discounted total."""
        pass


class NoDiscount(DiscountStrategy):
    """Returns the total unchanged (the default for every Order)."""

    def apply(self, total: float) -> float:
        return total


class PercentageDiscount(DiscountStrategy):
    """Takes a percentage off, e.g. PercentageDiscount(10) takes 10% off."""

    def __init__(self, percentage: float):
        if percentage <= 0 or percentage > 100:
            raise ValueError("Percentage must be greater than 0 and at most 100.")
        self.__percentage: float = percentage

    def apply(self, total: float) -> float:
        return total * (1 - self.__percentage / 100)


class BulkDiscount(DiscountStrategy):
    """Takes a fixed amount off any total at or above a threshold,
    e.g. BulkDiscount(200, 20) takes 20 off any total of 200 or more."""

    def __init__(self, threshold: float, amount: float):
        if threshold < 0 or amount <= 0:
            raise ValueError("Threshold cannot be negative and amount must be greater than zero.")
        self.__threshold: float = threshold
        self.__amount: float = amount

    def apply(self, total: float) -> float:
        if total >= self.__threshold:
            return max(total - self.__amount, 0.0)
        return total