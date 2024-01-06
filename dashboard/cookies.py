"""
Creates cookies for the Dashboard.
"""
import extra_streamlit_components as stx
from extra_streamlit_components.CookieManager import CookieManager


def set_cookies(user: dict, cookie_manager: CookieManager):
    """
    Sets the cookies to be stored for each login.
    """
    cookie_manager.set("logged_in", "True", max_age=86400)
    cookie_manager.set("user_email", user["email"], max_age=86400)
    cookie_manager.set("user_id", str(user["user_id"]), max_age=86400)


def clear_cookies_of_session(cookie_manager: CookieManager) -> None:
    """
    Clears the cookies that were stored in that session.
    """
    cookie_manager.delete("logged_in")
    cookie_manager.delete("user_email")
    cookie_manager.delete("user_id")
