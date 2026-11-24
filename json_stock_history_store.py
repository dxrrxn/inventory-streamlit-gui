import json
import os

from daily_stock_record import DailyStockRecord
from stock_history_store import StockHistoryStore


class JsonStockHistoryStore(StockHistoryStore):
    """Keeps one store's daily stock records in a JSON file, e.g. stores/kovan_history.json."""

    def __init__(self, path: str):
        self.__path: str = path

    @property
    def name(self) -> str:
        return f"JSON file ({os.path.basename(self.__path)})"

    def __read(self) -> list[dict]:
        if not os.path.exists(self.__path):
            return []
        try:
            with open(self.__path) as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise OSError(f"{os.path.basename(self.__path)} is damaged: {error}") from error
        if not isinstance(data, list):
            raise OSError(f"{os.path.basename(self.__path)} is damaged: expected a list")
        return data

    def load(self) -> list[DailyStockRecord]:
        records = []
        for item in self.__read():
            try:
                records.append(DailyStockRecord.from_dict(item))
            except (KeyError, TypeError, ValueError):
                continue                        # a damaged day doesn't hide the others
        return sorted(records, key=lambda record: record.get_day())

    def save(self, record: DailyStockRecord) -> bool:
        try:
            day = record.get_day().isoformat()
            data = [item for item in self.__read() if item.get("date") != day]
            data.append(record.to_dict())
            data.sort(key=lambda item: str(item.get("date")))
            folder = os.path.dirname(self.__path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            temporary = self.__path + ".tmp"            # write a copy, then swap it in
            with open(temporary, "w") as file:
                json.dump(data, file, indent=4)
            os.replace(temporary, self.__path)
        except OSError:
            return False
        return True
