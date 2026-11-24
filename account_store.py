from abc import ABC, abstractmethod


class AccountStore(ABC):
    """Interface: where the login accounts are kept (a JSON file or MongoDB).
    Accounts are passed as dictionaries made by Account.to_dict()."""

    @abstractmethod
    def load(self) -> list[dict]:
        """Every saved account ([] if none yet). Raises OSError if they can't be read."""

    @abstractmethod
    def save(self, accounts: list[dict]) -> bool:
        """Replace the saved accounts. Returns True if it worked."""
