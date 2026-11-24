import hashlib
import hmac
import os
from abc import ABC, abstractmethod

MIN_PASSWORD_LENGTH = 8


class Account(ABC):
    """Abstract login account. Passwords are never stored, only a salted hash
    (PBKDF2-SHA256), so a stolen accounts file doesn't reveal them.

    Subclasses decide which stores the account may open (polymorphism):
    an EmployeeAccount opens one store, the MasterAccount opens them all.
    """

    ROLE = ""
    ITERATIONS = 200_000

    def __init__(self, username: str, password_hash: str, salt: str):
        username = str(username).strip()
        if not username:
            raise ValueError("Username cannot be empty.")
        self.__username: str = username
        self.__password_hash: str = password_hash
        self.__salt: str = salt

    @classmethod
    def hash_password(cls, password: str, salt: str | None = None) -> tuple[str, str]:
        """Return (hash, salt) for a new password. Raises ValueError if it is too short."""
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        salt = salt or os.urandom(16).hex()
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), cls.ITERATIONS)
        return digest.hex(), salt

    def get_username(self) -> str:
        return self.__username

    def check_password(self, password: str) -> bool:
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(self.__salt),
                                     self.ITERATIONS)
        return hmac.compare_digest(digest.hex(), self.__password_hash)   # same time for every guess

    def set_password(self, password: str) -> None:
        self.__password_hash, self.__salt = self.hash_password(password)

    def to_dict(self) -> dict:
        return {"username": self.__username, "role": self.ROLE,
                "password_hash": self.__password_hash, "salt": self.__salt}

    @abstractmethod
    def can_access(self, branch_name: str) -> bool:
        """True if this account may open the store with this name."""

    @abstractmethod
    def is_master(self) -> bool:
        """True for the master login, which sees every store and manages staff."""

    @abstractmethod
    def describe(self) -> str:
        """Who this is, for the sidebar, e.g. "Sengkang staff"."""
