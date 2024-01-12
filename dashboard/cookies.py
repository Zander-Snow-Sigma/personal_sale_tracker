"""
Creates cookies for the Dashboard.
"""
from extra_streamlit_components.CookieManager import CookieManager


def set_cookies(user: dict, cookie_manager: CookieManager):
    """
    Sets the cookies to be stored for each login.
    """
    cookie_manager.set("logged_in", "True", max_age=86400, key="new")
    cookie_manager.set("user_email", user["email"], max_age=86400, key="old")
    cookie_manager.set("user_id", str(user["user_id"]), max_age=86400)


def clear_cookies_of_session(cookie_manager: CookieManager) -> None:
    """
    Clears the cookies that were stored in that session.
    """
    cookie_manager.delete("logged_in", key="del")
    cookie_manager.delete("user_email", key="dele")
    cookie_manager.delete("user_id")
