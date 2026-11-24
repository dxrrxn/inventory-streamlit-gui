"""Shared set-up for the GUI and storage tests: a temporary app folder with a copy
of the sample inventory.json, a master and two employee accounts, and fast
password hashing (the real app uses 200,000 rounds; the tests use 1,000)."""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from account import Account
from account_manager import AccountManager
from fake_mongo import FakeCollection
from fake_streamlit import FakeStreamlit, RerunRequested
from store_factory import StoreFactory
from streamlit_app import InventoryGui, APP_DIR

MASTER_PASSWORD = "master-pass-1"
STAFF_PASSWORD = "staff-pass-1"


class FakeDatabase(dict):
    """A MongoDB database stand-in: database["name"] gives a FakeCollection."""

    def __missing__(self, name):
        self[name] = FakeCollection(name)
        return self[name]


class AppTestCase(unittest.TestCase):

    def setUp(self):
        patcher = patch.object(Account, "ITERATIONS", 1000)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        shutil.copy(os.path.join(APP_DIR, "inventory.json"), os.path.join(self.folder, "inventory.json"))
        self.factory = self.make_factory()
        self.state = {}

    def make_factory(self) -> StoreFactory:
        return StoreFactory(self.folder)                 # JSON files in the temporary folder

    def add_accounts(self) -> AccountManager:
        accounts = AccountManager(self.factory.account_store())
        accounts.create_master("boss", MASTER_PASSWORD)
        accounts.add_employee("amy", STAFF_PASSWORD, "Kovan")
        accounts.add_employee("ben", STAFF_PASSWORD, "Punggol")
        return accounts

    def log_in(self, username: str) -> None:
        """Skip the login screen: put the account straight into the session."""
        self.state["user"] = AccountManager(self.factory.account_store()).find(username)

    def show(self, page=None, inputs=None, clicks=()):
        """Draw the app once, like one Streamlit run. Returns the fake and whether it asked to rerun."""
        inputs = dict(inputs or {})
        if page is not None:
            inputs.setdefault("master_page" if page in InventoryGui.MASTER_PAGES else "page", page)
        ui = FakeStreamlit(inputs=inputs, clicks=clicks, session_state=self.state)
        try:
            InventoryGui(ui, self.factory).run()
            rerun = False
        except RerunRequested:
            rerun = True
        return ui, rerun

    def branch(self, name: str = "Kovan"):
        return self.state["branches"][name]

    def inventory(self, name: str = "Kovan"):
        return self.branch(name).get_inventory()
