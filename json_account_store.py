import json
import os

from account_store import AccountStore


class JsonAccountStore(AccountStore):
    """Keeps the login accounts in a JSON file (accounts.json, which is not committed to Git)."""

    def __init__(self, path: str):
        self.__path: str = path

    def load(self) -> list[dict]:
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

    def save(self, accounts: list[dict]) -> bool:
        try:
            with open(self.__path, "w") as file:
                json.dump(accounts, file, indent=4)
        except OSError:
            return False
        return True
