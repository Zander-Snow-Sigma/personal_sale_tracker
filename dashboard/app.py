"""
Streamlit app that runs the Dashboard.
"""
import logging
import webbrowser

import bcrypt
from dotenv import load_dotenv
import extra_streamlit_components as stx
from extra_streamlit_components.CookieManager import CookieManager
import pandas as pd
import streamlit as st

from cookies import set_cookies, clear_cookies_of_session
from database import get_database_connection, load_all_database_info, get_user_info
from rendering import render_dashboard, render_login_page

WEBSITE_URL = "http://3.10.142.198:5000/"


def authenticate_user(users: list[dict], email: str, password: str) -> dict | None:
    """
    Authenticates each user and only returns the user 
    from the RDS if the details entered match, otherwise returns None.
    """
    for user in users:
        if email == user["email"] and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
            return user
    return None


def handle_login(users: list[dict], email: str,
                 password: str, cookie_manager: CookieManager):
    """
    If the user is authenticated the session state details 
    are changed and cookies are set.
    If the user can't be authenticated 
    i.e. details are incorrect they will stay on the login page.
    """
    user = authenticate_user(users, email, password)
    if user:
        st.session_state['logged_in'] = True
        st.session_state['user_email'] = user["email"]
        st.session_state['user_id'] = user["user_id"]
        set_cookies(user, cookie_manager)
        st.experimental_rerun()
    else:
        st.error("Invalid email or password.")


def logout_of_dashboard(cookie_manager: CookieManager) -> None:
    """
    Logs the user out of the dashboard and returns them to the login page.
    """
    st.session_state['logged_in'] = False
    st.session_state['user_email'] = ''
    st.session_state['user_id'] = ''
    clear_cookies_of_session(cookie_manager)
    st.rerun()


def main_display():
    """
    Main function script to run the entire streamlit app.
    """
    load_dotenv()
    logging.info("loaded env variables")
    cookie_manager = stx.CookieManager()

    logging.info("Loaded cookie manager")

    users = get_user_info(get_database_connection())

    # Check login state
    logged_in = cookie_manager.get("logged_in")
    user_email = cookie_manager.get("user_email")
    user_id = cookie_manager.get("user_id")

    if logged_in and user_email and user_id:
        st.session_state['logged_in'] = logged_in == 'True'
        st.session_state['user_email'] = user_email
        st.session_state['user_id'] = int(user_id)

    # Render login page or dashboard
    if not st.session_state.get('logged_in'):
        email, password = render_login_page()
        if st.button("Login"):
            handle_login(users, email, password, cookie_manager)
    else:
        df = pd.DataFrame(load_all_database_info(get_database_connection()))
        render_dashboard(df, users)

        st.sidebar.link_button("SaleTracker Website", WEBSITE_URL)

        if st.sidebar.button("Logout"):
            logout_of_dashboard(cookie_manager)


if __name__ == "__main__":
    load_dotenv()
    main_display()
