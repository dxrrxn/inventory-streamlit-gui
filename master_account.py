from account import Account


class MasterAccount(Account):
    """The master login: can open every store and manage the employee accounts."""

    ROLE = "master"

    def can_access(self, branch_name: str) -> bool:
        return True

    def is_master(self) -> bool:
        return True

    def describe(self) -> str:
        return "Master (all stores)"
