from pymongo.errors import PyMongoError

from account_store import AccountStore


class MongoAccountStore(AccountStore):
    """Keeps the login accounts in a MongoDB collection, one document per account."""

    HIDE_ID = {"_id": 0}

    def __init__(self, collection):
        self.__collection = collection

    def load(self) -> list[dict]:
        try:
            return list(self.__collection.find({}, self.HIDE_ID).sort("_id", 1))
        except PyMongoError as error:
            raise OSError(f"Could not read the accounts from MongoDB: {error}") from error

    def save(self, accounts: list[dict]) -> bool:
        keep = {account["username"] for account in accounts}
        try:
            for account in accounts:
                self.__collection.replace_one({"username": account["username"]}, dict(account), upsert=True)
            for old in list(self.__collection.find({}, self.HIDE_ID)):
                if old.get("username") not in keep:
                    self.__collection.delete_many({"username": old.get("username")})
        except PyMongoError:
            return False
        return True
