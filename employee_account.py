from account import Account
from branch import BRANCH_NAMES


class EmployeeAccount(Account):
    """A store employee: can open only the one store they work at."""

    ROLE = "employee"

    def __init__(self, username: str, password_hash: str, salt: str, branch_name: str,
                 name: str = ""):
        super().__init__(username, password_hash, salt, name)
        if branch_name not in BRANCH_NAMES:
            raise ValueError(f"Unknown store: {branch_name}")
        self.__branch_name: str = branch_name

    def get_branch_name(self) -> str:
        return self.__branch_name

    def can_access(self, branch_name: str) -> bool:
        return branch_name == self.__branch_name

    def is_master(self) -> bool:
        return False

    def describe(self) -> str:
        return f"{self.__branch_name} staff"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["store"] = self.__branch_name
        return data
