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
        name = ui.text_input("Your name", key="setup_name", placeholder="e.g. Darren Ng").strip()
        username = ui.text_input("Master username", value="master", key="setup_user").strip()
        password = ui.text_input("Password", type="password", key="setup_password")
        confirm = ui.text_input("Confirm password", type="password", key="setup_confirm")
        if not ui.button("Create master account", key="setup_button", type="primary"):
            return
        if password != confirm:
            ui.error("The passwords don't match.")
            return
        try:
            self.__accounts.create_master(username, password, name)
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
        self.__done(f"Welcome, {account.get_name()}.")

    def manage_staff(self) -> None:
        """Master only: list, add, rename, reset and remove employee logins."""
        ui = self.__ui
        ui.subheader("Manage staff")
        employees = self.__accounts.get_employees()
        if employees:
            ui.dataframe([{"Name": e.get_name(), "Username": e.get_username(), "Store": e.get_branch_name()}
                          for e in employees], hide_index=True)
        else:
            ui.info("No employee accounts yet.")

        ui.markdown("**Add an employee**")
        first, second = ui.columns(2)
        name = first.text_input("Name", key="staff_name", placeholder="e.g. Amy Tan").strip()
        username = second.text_input("Username (used to log in)", key="staff_user").strip()
        first, second = ui.columns(2)
        branch = first.selectbox("Store", BRANCH_NAMES, key="staff_store")
        password = second.text_input("Password", type="password", key="staff_password")
        if ui.button("Add employee", key="staff_add", type="primary"):
            try:
                self.__accounts.add_employee(username, password, branch, name)
            except (ValueError, OSError) as error:
                ui.error(str(error))
            else:
                self.__done(f"{name or username} can now log in to {branch} as {username}.")

        master = ui.session_state["user"]
        accounts = [master] + employees
        labels = {a.get_username(): f"{a.get_name()} ({a.get_username()})" for a in accounts}
        usernames = list(labels)

        ui.markdown("**Change a name**")
        first, second = ui.columns(2)
        who = first.selectbox("Account", usernames, key="rename_user", format_func=labels.get)
        new_name = second.text_input("New name", key=f"rename_name_{who}",
                                     value=self.__accounts.find(who).get_name())
        if ui.button("Change name", key="rename_button"):
            try:
                self.__accounts.rename(who, new_name)
            except (ValueError, OSError) as error:
                ui.error(str(error))
            else:
                self.__done(f"{who} is now shown as {new_name.strip()}.")

        ui.markdown("**Reset a password**")
        first, second = ui.columns(2)
        who = first.selectbox("Account", usernames, key="reset_user", format_func=labels.get)
        new_password = second.text_input("New password", type="password", key="reset_password")
        if ui.button("Reset password", key="reset_button"):
            try:
                self.__accounts.reset_password(who, new_password)
            except (ValueError, OSError) as error:
                ui.error(str(error))
            else:
                self.__done(f"Password for {labels[who]} changed.")

        if employees:
            ui.markdown("**Remove an employee**")
            who = ui.selectbox("Employee", usernames[1:], key="remove_user", format_func=labels.get)
            sure = ui.checkbox(f"Yes, remove {labels[who]}'s login", key=f"remove_user_sure_{who}")
            if ui.button("Remove employee", key="remove_user_button", disabled=not sure):
                try:
                    self.__accounts.remove_employee(who)
                except (ValueError, OSError) as error:
                    ui.error(str(error))
                else:
                    self.__done(f"{labels[who]} removed.")
