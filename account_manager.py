from account import Account
from account_store import AccountStore
from employee_account import EmployeeAccount
from master_account import MasterAccount


class AccountManager:
    """The login accounts: one master and any number of employees (SRP: accounts only).

    Aggregation: it is given the AccountStore (JSON file or MongoDB) to keep them in.
    Usernames are not case-sensitive. User mistakes raise ValueError; a failed
    save raises OSError, so the caller can show either.
    """

    def __init__(self, account_store: AccountStore):
        self.__account_store: AccountStore = account_store
        self.__accounts: list[Account] = [self.__from_dict(data) for data in account_store.load()]

    @staticmethod
    def __from_dict(data: dict) -> Account:
        """Factory: build the right Account subclass for a saved record."""
        name = data.get("name", "")                # accounts saved before names existed have none
        if data["role"] == MasterAccount.ROLE:
            return MasterAccount(data["username"], data["password_hash"], data["salt"], name)
        return EmployeeAccount(data["username"], data["password_hash"], data["salt"], data["store"], name)

    def __save(self) -> None:
        if not self.__account_store.save([account.to_dict() for account in self.__accounts]):
            raise OSError("The accounts could not be saved. Please try again.")

    def find(self, username: str) -> Account | None:
        for account in self.__accounts:
            if account.get_username().lower() == username.strip().lower():
                return account
        return None

    def has_master(self) -> bool:
        return any(account.is_master() for account in self.__accounts)

    def get_employees(self) -> list[EmployeeAccount]:
        employees = [account for account in self.__accounts if not account.is_master()]
        return sorted(employees, key=lambda e: (e.get_branch_name(), e.get_username().lower()))

    def login(self, username: str, password: str) -> Account | None:
        """The account if the username and password match, otherwise None
        (the same answer for a wrong username or a wrong password)."""
        account = self.find(username)
        if account is not None and account.check_password(password):
            return account
        return None

    def create_master(self, username: str, password: str, name: str = "") -> MasterAccount:
        """First-time setup only: there can be just one master account."""
        if self.has_master():
            raise ValueError("A master account already exists.")
        password_hash, salt = Account.hash_password(password)
        master = MasterAccount(username, password_hash, salt, name)
        self.__accounts.append(master)
        self.__save()
        return master

    def add_employee(self, username: str, password: str, branch_name: str,
                     name: str = "") -> EmployeeAccount:
        if self.find(username) is not None:
            raise ValueError(f"The username {username.strip()} is already taken.")
        password_hash, salt = Account.hash_password(password)
        employee = EmployeeAccount(username, password_hash, salt, branch_name, name)
        self.__accounts.append(employee)
        self.__save()
        return employee

    def reset_password(self, username: str, password: str) -> None:
        account = self.find(username)
        if account is None:
            raise ValueError("No such account.")
        account.set_password(password)
        self.__save()

    def rename(self, username: str, name: str) -> None:
        """Change the name shown for an account (the username stays the same)."""
        account = self.find(username)
        if account is None:
            raise ValueError("No such account.")
        account.set_name(name)
        self.__save()

    def remove_employee(self, username: str) -> None:
        account = self.find(username)
        if account is None or account.is_master():
            raise ValueError("Only employee accounts can be removed.")
        self.__accounts.remove(account)
        self.__save()
