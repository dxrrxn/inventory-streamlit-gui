import datetime

from inventory import Inventory

SINGAPORE = datetime.timezone(datetime.timedelta(hours=8))   # no daylight saving in Singapore


class DailyStockRecord:
    """The leftover (closing) stock of every product in one store at the end of one day.

    It is a snapshot: later stock changes don't alter it, so past days can be compared.
    """

    def __init__(self, store: str, day: datetime.date, counts: list[dict], recorded_by: str,
                 recorded_at: str = ""):
        self.__store: str = store
        self.__day: datetime.date = day
        self.__counts: list[dict] = [dict(count) for count in counts]   # a copy: never changed later
        self.__recorded_by: str = recorded_by
        self.__recorded_at: str = recorded_at or datetime.datetime.now(SINGAPORE).isoformat(
            timespec="seconds")

    @staticmethod
    def today() -> datetime.date:
        return datetime.datetime.now(SINGAPORE).date()

    @classmethod
    def from_inventory(cls, store: str, day: datetime.date, inventory: Inventory,
                       recorded_by: str) -> "DailyStockRecord":
        """Take the snapshot: each product's stock and PAR level right now."""
        if day > cls.today():
            raise ValueError("You can't record stock for a day that hasn't happened yet.")
        counts = [{"id": p.get_product_id(), "brand": p.get_brand().get_name(), "name": p.get_name(),
                   "stock": p.get_stock(), "par": p.get_par_level()}
                  for p in inventory.get_products()]
        return cls(store, day, counts, recorded_by)

    def get_store(self) -> str:
        return self.__store

    def get_day(self) -> datetime.date:
        return self.__day

    def get_counts(self) -> list[dict]:
        return [dict(count) for count in self.__counts]

    def get_recorded_by(self) -> str:
        return self.__recorded_by

    def get_recorded_at(self) -> str:
        return self.__recorded_at

    def total_units(self) -> int:
        return sum(count["stock"] for count in self.__counts)

    def below_par_count(self) -> int:
        return sum(1 for count in self.__counts if count["stock"] < count["par"])

    def stock_of(self, product_id: str) -> int | None:
        """This product's leftover stock that day, or None if it wasn't stocked then."""
        for count in self.__counts:
            if count["id"] == product_id:
                return count["stock"]
        return None

    def compare_with(self, previous: "DailyStockRecord | None") -> list[dict]:
        """One row per product, with the change since the previous record (None if new)."""
        rows = []
        for count in self.__counts:
            before = previous.stock_of(count["id"]) if previous is not None else None
            rows.append({**count, "change": None if before is None else count["stock"] - before})
        return rows

    def to_dict(self) -> dict:
        return {"store": self.__store, "date": self.__day.isoformat(), "counts": self.get_counts(),
                "recorded_by": self.__recorded_by, "recorded_at": self.__recorded_at}

    @classmethod
    def from_dict(cls, data: dict) -> "DailyStockRecord":
        """Rebuild a saved record. Raises KeyError, TypeError or ValueError if it is damaged."""
        counts = data["counts"]
        for count in counts:
            if not isinstance(count["stock"], int) or not isinstance(count["par"], int):
                raise ValueError("Stock and PAR must be whole numbers.")
        return cls(data["store"], datetime.date.fromisoformat(data["date"]), counts,
                   data.get("recorded_by", ""), data.get("recorded_at", ""))
