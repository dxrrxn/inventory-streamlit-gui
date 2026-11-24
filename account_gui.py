"""
The account screens of the Streamlit GUI: first-time setup, login and Manage staff.
"""
from __future__ import annotations

from account import MIN_PASSWORD_LENGTH
from account_manager import AccountManager
from branch import BRANCH_NAMES


class AccountGui:
    """SRP: only the login and account screens; InventoryGui does the inventory pages.
    Aggregation: it is given the AccountManager. A successful login puts the
    Account in session_state["user"]."""

    def __init__(self, ui, accounts: AccountManager):
        self.__ui = ui
        self.__accounts = accounts

    def __done(self, message: str) -> None:
        self.__ui.session_state["flash"] = message
        self.__ui.rerun()

    def setup(self) -> None:
        """Shown once, when there is no master account yet."""
        _, middle, _ = self.__ui.columns([1, 1.4, 1])         # a narrow card in the middle
        with middle:
            self.__setup_form()

    def __setup_form(self) -> None:
        ui = self.__ui
        ui.subheader("First-time setup: create the master account")
        ui.caption(f"The master can open every store and manage staff logins. "
                   f"Use a password of at least {MIN_PASSWORD_LENGTH} characters.")
        username = ui.text_input("Master username", value="master", key="setup_user").strip()
        password = ui.text_input("Password", type="password", key="setup_password")
        confirm = ui.text_input("Confirm password", type="password", key="setup_confirm")
        if not ui.button("Create master account", key="setup_button", type="primary"):
            return
        if password != confirm:
            ui.error("The passwords don't match.")
            return
        try:
            self.__accounts.create_master(username, password)
        except (ValueError, OSError) as error:
            ui.error(str(error))
            return
        self.__done("Master account created. Please log in.")

    def login(self) -> None:
        _, middle, _ = self.__ui.columns([1, 1.4, 1])         # a narrow card in the middle
        with middle:
            self.__login_form()

    def __login_form(self) -> None:
        ui = self.__ui
        ui.subheader("Staff login")
        ui.markdown('<p class="sx-login-note">Sengkang · Punggol · Hougang · Kovan · Serangoon</p>',
                    unsafe_allow_html=True)
        username = ui.text_input("Username", key="login_user")
        password = ui.text_input("Password", type="password", key="login_password")
        if not ui.button("Log in", key="login_button", type="primary"):
            return
        account = self.__accounts.login(username, password)
        if account is None:
            ui.error("Wrong username or password.")     # never say which one was wrong
            return
        ui.session_state["user"] = account
        self.__done(f"Welcome, {account.get_username()}.")

    def manage_staff(self) -> None:
        """Master only: list, add, reset and remove employee logins."""
        ui = self.__ui
        ui.subheader("Manage staff")
        employees = self.__accounts.get_employees()
        if employees:
            ui.dataframe([{"Username": e.get_username(), "Store": e.get_branch_name()}
                          for e in employees], hide_index=True)
        else:
            ui.info("No employee accounts yet.")

        ui.markdown("**Add an employee**")
        first, second = ui.columns(2)
        username = first.text_input("Username", key="staff_user").strip()
        branch = second.selectbox("Store", BRANCH_NAMES, key="staff_store")
        password = ui.text_input("Password", type="password", key="staff_password")
        if ui.button("Add employee", key="staff_add", type="primary"):
            try:
                self.__accounts.add_employee(username, password, branch)
            except (ValueError, OSError) as error:
                ui.error(str(error))
            else:
                self.__done(f"{username} can now log in to {branch}.")

        names = [e.get_username() for e in employees]
        master = ui.session_state["user"].get_username()
        ui.markdown("**Reset a password**")
        first, second = ui.columns(2)
        who = first.selectbox("Account", [master] + names, key="reset_user")
        new_password = second.text_input("New password", type="password", key="reset_password")
        if ui.button("Reset password", key="reset_button"):
            try:
                self.__accounts.reset_password(who, new_password)
            except (ValueError, OSError) as error:
                ui.error(str(error))
            else:
                self.__done(f"Password for {who} changed.")

        if names:
            ui.markdown("**Remove an employee**")
            who = ui.selectbox("Employee", names, key="remove_user")
            sure = ui.checkbox(f"Yes, remove {who}'s login", key=f"remove_user_sure_{who}")
            if ui.button("Remove employee", key="remove_user_button", disabled=not sure):
                try:
                    self.__accounts.remove_employee(who)
                except (ValueError, OSError) as error:
                    ui.error(str(error))
                else:
                    self.__done(f"{who} removed.")
