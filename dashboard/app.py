import streamlit as st
import extra_streamlit_components as stx
import pandas as pd
from psycopg2 import connect, extras
from psycopg2.extensions import connection
import webbrowser

from dotenv import load_dotenv

from database import get_database_connection, load_all_database_info

load_dotenv()

widget_id = (id for id in range(1, 100_00))


# Initialize the Cookie Manager
cookie_manager = stx.CookieManager()

# Users list with user IDs


def get_user_info(conn):

    all_users = [
        {"user_id": 0, "email": "admin@saletracker.co.uk",
         "password": "adminPassword", "type": "admin", "first_name": "Admin", "last_name": "Admin"},
    ]

    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT * FROM users;")

    users = cur.fetchall()

    for user in users:
        user["password"] = 'userPassword'
        user["type"] = 'user'
        all_users.append(user)
    return all_users


users = get_user_info(get_database_connection())


def authenticate_user(users, email, password):
    for user in users:
        if email == user["email"] and password == user["password"]:
            return user
    return None


logged_in = cookie_manager.get("logged_in")
user_email = cookie_manager.get("user_email")
user_id = cookie_manager.get("user_id")

if logged_in and user_email and user_id:
    st.session_state['logged_in'] = logged_in == 'True'
    st.session_state['user_email'] = user_email
    st.session_state['user_id'] = int(user_id)

# Login Page
if not st.session_state.get('logged_in'):
    st.markdown("""
        <h1>
            <center><span style='color: #007bff;'>Sale</span>Tracker Dashboard</center>
        </h1>
        <h2><center>Please Login</center></h2>
        """, unsafe_allow_html=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = authenticate_user(users, email, password)
        if user:
            st.session_state['logged_in'] = True
            st.session_state['user_email'] = user["email"]
            st.session_state['user_id'] = user["user_id"]
            # Set cookies
            cookie_manager.set("logged_in", "True",
                               max_age=86400, key=next(widget_id))
            cookie_manager.set(
                "user_email", user["email"], max_age=86400, key=next(widget_id))
            cookie_manager.set("user_id", str(
                user["user_id"]), max_age=86400, key=next(widget_id))
            st.experimental_rerun()
        else:
            st.error("Invalid email or password.")

else:
    st.markdown("""
        <h1 style='display: inline; font-size: 4em; margin-top: 0; padding-top: 0;'>
            <span style='color: #007bff;'>Sale</span>Tracker Dashboard
        </h1>
        """, unsafe_allow_html=True)

    # Load data from database
    conn = get_database_connection()
    data = load_all_database_info(conn)
    df = pd.DataFrame(data)

    # Admin Dashboard
    if st.session_state.get('user_id') == 0:
        st.write(
            f"Welcome, {st.session_state['user_email']}! You're logged in to the Admin Dashboard.")
        # Admin-specific functionality goes here

        admin_df = pd.DataFrame(users)

        st.table(admin_df.loc[:, admin_df.columns != "password"])

        st.sidebar.title('Product Image Viewer')
        # Select a product
        selected_product_name = st.sidebar.selectbox(
            'Select a Product', df['Product Name'].unique())

        # Find the image URL for the selected product
        image_url = df[df['Product Name'] ==
                       selected_product_name]['Image URL'].iloc[0]

        # Display the Image URL
        st.sidebar.image(image_url)

     # User-specific Dashboards
    else:
        # Filter the DataFrame for the logged-in user's data
        user_specific_df = df[df['User ID'] == st.session_state['user_id']]

        st.write(
            f"Welcome, {st.session_state['user_email']}! You're logged in.")

        st.sidebar.title('Product Image Viewer')
        # Select a product
        selected_product_name = st.sidebar.selectbox(
            'Select a Product', user_specific_df['Product Name'].unique())
        image_url = df[df['Product Name'] ==
                       selected_product_name]['Image URL'].iloc[0]

        # Display the Image URL
        st.sidebar.image(image_url)

        sorted_df = user_specific_df.sort_values(
            by=['Product ID', 'Updated At'], ascending=[True, False])
        most_recent_prices = sorted_df.groupby('Product ID').first()

        st.write(f"Dashboard for User ID {st.session_state['user_id']}")

        st.table(most_recent_prices)

    url = "http://18.130.21.247:5000/"
    if st.sidebar.button("SaleTracker Website", key=next(widget_id)):
        webbrowser.open_new_tab(url)

    # Logout button
    if st.sidebar.button("Logout", key=next(widget_id)):
        st.session_state['logged_in'] = False
        st.session_state['user_email'] = ''
        st.session_state['user_id'] = ''
        # Clear cookies
        cookie_manager.delete("logged_in", key=next(widget_id))
        cookie_manager.delete("user_email", key=next(widget_id))
        cookie_manager.delete("user_id", key=next(widget_id))
        st.experimental_rerun()
