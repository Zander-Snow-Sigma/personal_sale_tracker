import webbrowser

import pandas as pd
from pandas import DataFrame
import streamlit as st

from visualisations import (get_latest_price_readings,
                            get_popularity_of_products,
                            get_price_of_products_over_time)

FIRST_PRODUCT = 0
DEFAULT_MIN = 1
DEFAULT_PRODUCT = 3


def render_login_page() -> tuple:
    """
    Returns the input buttons for the login page and creates the login page.
    """
    st.markdown("""
        <h1>
            <center><span style='color: #007bff;'>Sale</span>Tracker Dashboard</center>
        </h1>
        <h2><center>Please Login</center></h2>
        """, unsafe_allow_html=True)
    email = st.text_input("Email", key="email_input")
    password = st.text_input("Password", type="password", key="password_input")
    return email, password


def get_most_recent_price(most_recent: DataFrame):
    """
    Returns the most recent price information.
    """
    sorted_product_df = most_recent.sort_values(
        by='Updated At', ascending=False)
    most_recent_price = sorted_product_df.iloc[0]
    return most_recent_price


def get_price_info(most_recent: DataFrame, sort_value):
    """
    Displays the price information for the most recent price for a particular product. 
    If sort_value is False the highest price is returned. 
    If the sort_value is True the lowest price is returned.
    """
    sorted_product_df = most_recent.sort_values(
        by='Price', ascending=sort_value)
    price = sorted_product_df.iloc[0]
    return price


def render_product_image_viewer(df: DataFrame) -> None:
    """
    Creates a sidebar element that shows the image of the product
    depending on the product selected in the selectbox.
    """
    st.sidebar.title('Product Image Viewer')
    selected_product_name = st.sidebar.selectbox(
        'Select a Product', df['Product Name'].unique())
    filtered_df = df[df['Product Name'] == selected_product_name]
    if not filtered_df.empty:

        image_url = filtered_df['Image URL'].iloc[0]
        st.sidebar.image(image_url)

        most_recent_price = get_most_recent_price(filtered_df)
        st.sidebar.write(
            f'Current price: £{round(most_recent_price["Price"], 2)}')

        highest_price = get_price_info(filtered_df, False)
        st.sidebar.write(
            f'Highest Price: £{round(highest_price["Price"], 2)}')

        lowest_price = get_price_info(filtered_df, True)
        st.sidebar.write(f'Lowest Price: £{round(lowest_price["Price"], 2)}')

        if most_recent_price["Product Availability"] == True:
            st.sidebar.write(
                f'Availability: In Stock')
        else:
            st.sidebar.write(
                f'Availability: Out of Stock')

        if st.sidebar.button("Go to Product"):
            webbrowser.open_new_tab(most_recent_price["Product URL"])
    else:
        st.sidebar.write("No image available for the selected product.")


def display_admin_main_body(df: DataFrame) -> None:
    """
    Displays all of the admin main body for streamlit.
    """
    sorted_df = df.sort_values(
        by=['Product ID', 'Updated At'], ascending=[True, False])
    most_recent_prices = sorted_df.groupby('Product ID').first()
    head_cols = st.columns(3)

    with head_cols[0]:
        st.metric("Total No. of Users :bust_in_silhouette:",
                  df["User Email"].nunique())
    with head_cols[1]:
        st.metric("Total No. of Products", df["Product Name"].nunique())

    with head_cols[2]:
        st.metric("Total No. of Subscriptions",
                  df["Subscription ID"].nunique())

    body_cols = st.columns(2)

    with body_cols[0]:
        selected_products_price = get_selected_products(
            most_recent_prices, "most_recent")
        name_in_selected_products_price = get_names_of_selected_products(
            most_recent_prices, selected_products_price)
        if not name_in_selected_products_price.any():
            st.error("Please select at least one product.")
        else:
            st.altair_chart(get_latest_price_readings(
                most_recent_prices[name_in_selected_products_price]), use_container_width=True)

    with body_cols[1]:
        selected_products = get_selected_products(df, "all_admin_pop")
        name_in_selected_products = get_names_of_selected_products(
            df, selected_products)
        if not name_in_selected_products.any():
            st.error("Please select at least one product.")
        else:
            st.altair_chart(get_popularity_of_products(df[name_in_selected_products]),
                            use_container_width=True)
            st.write("Popularity = The number of subscriptions each product has.")

    selected_products_all = get_selected_products(df, "all_admin")
    name_in_selected_products_all = get_names_of_selected_products(
        df, selected_products_all)
    st.altair_chart(get_price_of_products_over_time(df[name_in_selected_products_all]),
                    use_container_width=True)


def render_admin_dashboard(df: DataFrame, users: list[dict]) -> None:
    """
    Creates the admin dashboard to see all admin data.
    """
    st.markdown("""
        <h1>
            <center><span style='color: #007bff;'>Sale</span>Tracker Dashboard</center>
        </h1>
        """, unsafe_allow_html=True)
    st.write(
        f"Welcome, {st.session_state['user_email']}! You're logged in to the Admin Dashboard.")
    admin_df = pd.DataFrame(users)
    display_admin_main_body(df)
    st.title("User Information:")
    user_information = admin_df.loc[:, admin_df.columns != "password"]
    wanted_user = user_information[["user_id", "first_name",
                                    "last_name", "email"]]
    wanted_user.columns = ["User ID", "First Name", "Last Name", "Email"]
    st.dataframe(wanted_user, hide_index=True, use_container_width=True)
    render_product_image_viewer(df)


def get_selected_products(products: DataFrame, key_value: str) -> list:
    """
    Returns the selected plants in the sidebar.
    By Default this returns 10 plants.
    """
    if len(products["Product Name"].unique()) < 3:
        return st.multiselect(f"Selected Products",
                              list(products["Product Name"].unique()),
                              default=products["Product Name"].unique()[FIRST_PRODUCT:DEFAULT_MIN], placeholder="Please select a product...", key=key_value)

    else:

        return st.multiselect(f"Selected Products",
                              list(products["Product Name"].unique()),
                              default=products["Product Name"].unique()[FIRST_PRODUCT:DEFAULT_PRODUCT], placeholder="Please select a product...", key=key_value)


def get_names_of_selected_products(products: DataFrame, selected_products: list) -> pd.Series:
    """
    Returns the names of the selected plants in the sidebar.
    """
    return products["Product Name"].isin(selected_products)


def display_user_specific_data(df: DataFrame) -> None:
    """
    Creates a user specific display.
    """
    sorted_df = df.sort_values(
        by=['Product ID', 'Updated At'], ascending=[True, False])
    most_recent_prices = sorted_df.groupby('Product ID').first()

    head_cols = st.columns(2)

    with head_cols[0]:
        st.metric("Total No. of Products", df["Product Name"].nunique())

    with head_cols[1]:
        st.metric("Total Price of Products",
                  f'£{round(most_recent_prices["Price"].astype(float).sum(), 2)}')

    selected_products = get_selected_products(
        most_recent_prices, "recent_user")

    name_in_selected_products = get_names_of_selected_products(
        most_recent_prices, selected_products)

    if not name_in_selected_products.any():
        st.error("Please select at least one product.")
    else:
        st.altair_chart(get_latest_price_readings(
            most_recent_prices[name_in_selected_products]), use_container_width=True)

    selected_products_all = get_selected_products(
        df, "recent_user_all")

    name_in_selected_products_all = get_names_of_selected_products(
        df, selected_products_all)

    if not name_in_selected_products_all.any():
        st.error("Please select at least one Product.")
    else:
        st.altair_chart(get_price_of_products_over_time(df[name_in_selected_products_all]),
                        use_container_width=True)


def render_user_dashboard(df: DataFrame) -> None:
    """
    Creates the user dashboard in which each user will only be able to
    see information relevant to them.
    """
    user_specific_df = df[df['User ID'] == st.session_state['user_id']]
    st.markdown("""
        <h1>
            <center><span style='color: #007bff;'>Sale</span>Tracker Dashboard</center>
        </h1>
        """, unsafe_allow_html=True)
    st.write(f"Welcome, {st.session_state['user_email']}! You're logged in.")
    render_product_image_viewer(user_specific_df)
    display_user_specific_data(user_specific_df)


def render_dashboard(df: DataFrame, users: list[dict]) -> None:
    """
    Decides which dashboard to show depending on the type of account logged in.
    """
    if st.session_state.get('user_id') == 0:
        render_admin_dashboard(df, users)
    else:
        render_user_dashboard(df)
