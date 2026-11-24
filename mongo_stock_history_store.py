from pymongo.errors import PyMongoError

from daily_stock_record import DailyStockRecord
from stock_history_store import StockHistoryStore


class MongoStockHistoryStore(StockHistoryStore):
    """Keeps one store's daily stock records in a MongoDB collection, one document per day."""

    HIDE_ID = {"_id": 0}

    def __init__(self, collection, database_name: str):
        self.__collection = collection
        self.__database_name: str = database_name

    @property
    def name(self) -> str:
        return f"MongoDB ({self.__database_name})"

    def load(self) -> list[DailyStockRecord]:
        try:
            documents = list(self.__collection.find({}, self.HIDE_ID))
        except PyMongoError as error:
            raise OSError(f"Could not read the daily stock from MongoDB: {error}") from error
        records = []
        for document in documents:
            try:
                records.append(DailyStockRecord.from_dict(document))
            except (KeyError, TypeError, ValueError):
                continue
        return sorted(records, key=lambda record: record.get_day())

    def save(self, record: DailyStockRecord) -> bool:
        data = record.to_dict()
        try:
            self.__collection.replace_one({"date": data["date"]}, data, upsert=True)
        except PyMongoError:
            return False
        return True
