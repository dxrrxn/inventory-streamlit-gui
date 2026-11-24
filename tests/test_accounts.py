"""Tests for the login accounts: hashing, the master/employee rules and saving them."""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from account import Account
from account_manager import AccountManager
from branch import Branch, BRANCH_NAMES
from employee_account import EmployeeAccount
from fake_mongo import BrokenCollection, FakeCollection
from json_account_store import JsonAccountStore
from master_account import MasterAccount
from mongo_account_store import MongoAccountStore


class AccountTestCase(unittest.TestCase):

    def setUp(self):
        patcher = patch.object(Account, "ITERATIONS", 1000)      # fast hashing in tests
        patcher.start()
        self.addCleanup(patcher.stop)
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.path = os.path.join(self.folder, "accounts.json")
        self.accounts = AccountManager(JsonAccountStore(self.path))


class TestAccounts(AccountTestCase):

    def test_passwords_are_hashed_with_a_salt(self):
        first, salt_1 = Account.hash_password("same-password")
        second, salt_2 = Account.hash_password("same-password")
        self.assertNotEqual(first, second)                      # different salts, different hashes
        self.assertNotIn("same-password", first)
        self.assertEqual(Account.hash_password("same-password", salt_1)[0], first)

    def test_short_password_is_rejected(self):
        with self.assertRaises(ValueError):
            Account.hash_password("short")

    def test_master_opens_every_store_and_employee_only_theirs(self):
        master = self.accounts.create_master("boss", "master-pass-1")
        amy = self.accounts.add_employee("amy", "staff-pass-1", "Kovan")
        self.assertIsInstance(master, MasterAccount)
        self.assertIsInstance(amy, EmployeeAccount)
        self.assertTrue(all(master.can_access(name) for name in BRANCH_NAMES))
        self.assertEqual([name for name in BRANCH_NAMES if amy.can_access(name)], ["Kovan"])
        self.assertEqual(amy.describe(), "Kovan staff")
        self.assertTrue(master.is_master())
        self.assertFalse(amy.is_master())

    def test_login(self):
        self.accounts.create_master("boss", "master-pass-1")
        self.accounts.add_employee("Amy", "staff-pass-1", "Kovan")
        self.assertEqual(self.accounts.login("amy", "staff-pass-1").get_username(), "Amy")   # any case
        self.assertIsNone(self.accounts.login("amy", "wrong-pass-1"))
        self.assertIsNone(self.accounts.login("nobody", "staff-pass-1"))

    def test_only_one_master_and_unique_usernames(self):
        self.accounts.create_master("boss", "master-pass-1")
        with self.assertRaises(ValueError):
            self.accounts.create_master("boss2", "master-pass-1")
        self.accounts.add_employee("amy", "staff-pass-1", "Kovan")
        with self.assertRaises(ValueError):
            self.accounts.add_employee("AMY", "staff-pass-1", "Punggol")
        with self.assertRaises(ValueError):
            self.accounts.add_employee("cat", "staff-pass-1", "Orchard")     # not one of our stores

    def test_names(self):
        master = self.accounts.create_master("boss", "master-pass-1", "Darren Ng")
        amy = self.accounts.add_employee("amy", "staff-pass-1", "Kovan")
        self.assertEqual(master.get_name(), "Darren Ng")
        self.assertEqual(amy.get_name(), "amy")                         # no name given: the username
        self.accounts.rename("AMY", "  Amy   Tan ")
        self.assertEqual(amy.get_name(), "Amy Tan")                     # spaces tidied
        with self.assertRaises(ValueError):
            self.accounts.rename("amy", "x" * 61)
        again = AccountManager(JsonAccountStore(self.path))
        self.assertEqual(again.find("amy").get_name(), "Amy Tan")       # saved

    def test_accounts_saved_before_names_existed_still_load(self):
        password_hash, salt = Account.hash_password("staff-pass-1")
        with open(self.path, "w") as file:
            json.dump([{"username": "old", "role": "employee", "password_hash": password_hash,
                        "salt": salt, "store": "Kovan"}], file)
        self.assertEqual(AccountManager(JsonAccountStore(self.path)).find("old").get_name(), "old")

    def test_reset_and_remove(self):
        self.accounts.create_master("boss", "master-pass-1")
        self.accounts.add_employee("amy", "staff-pass-1", "Kovan")
        self.accounts.reset_password("amy", "new-pass-123")
        self.assertIsNotNone(self.accounts.login("amy", "new-pass-123"))
        self.assertIsNone(self.accounts.login("amy", "staff-pass-1"))
        with self.assertRaises(ValueError):
            self.accounts.remove_employee("boss")                 # the master can't be removed
        self.accounts.remove_employee("amy")
        self.assertIsNone(self.accounts.find("amy"))

    def test_accounts_are_saved_and_reloaded(self):
        self.accounts.create_master("boss", "master-pass-1")
        self.accounts.add_employee("ben", "staff-pass-1", "Punggol")
        with open(self.path) as file:
            self.assertNotIn("staff-pass-1", file.read())
        again = AccountManager(JsonAccountStore(self.path))
        self.assertTrue(again.has_master())
        self.assertEqual(again.login("ben", "staff-pass-1").get_branch_name(), "Punggol")

    def test_damaged_accounts_file_is_an_error_not_an_empty_list(self):
        with open(self.path, "w") as file:
            file.write("{not json")
        with self.assertRaises(OSError):
            AccountManager(JsonAccountStore(self.path))


class TestMongoAccountStore(unittest.TestCase):

    def test_save_and_load(self):
        collection = FakeCollection("accounts")
        store = MongoAccountStore(collection)
        store.save([{"username": "boss", "role": "master"}, {"username": "amy", "role": "employee"}])
        store.save([{"username": "boss", "role": "master"}])        # amy removed
        self.assertEqual(store.load(), [{"username": "boss", "role": "master"}])

    def test_lost_connection(self):
        store = MongoAccountStore(BrokenCollection())
        with self.assertRaises(OSError):
            store.load()
        self.assertFalse(store.save([]))


class TestBranch(unittest.TestCase):

    def test_only_our_five_stores(self):
        self.assertEqual(BRANCH_NAMES, ("Sengkang", "Punggol", "Hougang", "Kovan", "Serangoon"))
        self.assertEqual(Branch.key("Serangoon"), "serangoon")


if __name__ == "__main__":
    unittest.main()
