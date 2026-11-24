from abc import ABC, abstractmethod

from daily_stock_record import DailyStockRecord


class StockHistoryStore(ABC):
    """Interface: where one store's daily stock records are kept (a JSON file or MongoDB)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Where the records are kept, for the screen."""

    @abstractmethod
    def load(self) -> list[DailyStockRecord]:
        """Every saved record, oldest day first. Raises OSError if they can't be read.
        Damaged records are skipped."""

    @abstractmethod
    def save(self, record: DailyStockRecord) -> bool:
        """Add the record, replacing any record for the same day. Returns True if it worked."""
