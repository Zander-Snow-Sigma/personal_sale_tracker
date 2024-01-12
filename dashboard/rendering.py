"""
Script with rendering functions used to show streamlit displays.
"""
import pandas as pd
from pandas import DataFrame, Series
import streamlit as st

from visualisations import (get_latest_price_readings,
                            get_popularity_of_products,
                            get_price_of_products_over_time)

FIRST_PRODUCT = 0
DEFAULT_MIN = 1
DEFAULT_PRODUCT = 3
LOGO_URL = "./static/Logo.png"


def render_login_page() -> tuple:
    """
    Returns the input buttons for the login page and creates the login page.
    """
    col1, col2, col3 = st.columns(3)

    with col2:
        st.image(LOGO_URL, use_column_width=True)
    st.markdown("""
        <h3><center>Please Login</center></h3>
        """, unsafe_allow_html=True)

    # Prompts users to input their email and password.
    email = st.text_input("Email", key="email_input")
    password = st.text_input("Password", type="password", key="password_input")
    return email, password


def get_most_recent_price(most_recent: DataFrame) -> Series:
    """
    Returns the most recent price information.
    """
    sorted_product_df = most_recent.sort_values(
        by='Updated At', ascending=False)

    return sorted_product_df.iloc[0]


def get_price_info(most_recent: DataFrame, sort_value) -> Series:
    """
    Displays the price information for the most recent price for a particular product. 
    If sort_value is False the highest price is returned. 
    If the sort_value is True the lowest price is returned.
    """
    sorted_product_df = most_recent.sort_values(
        by='Price', ascending=sort_value)
    return sorted_product_df.iloc[0]


def render_sidebar(df: DataFrame) -> None:
    """
    Creates a sidebar element that shows the image of the product
    depending on the product selected in the selectbox.
    """
    st.sidebar.title('Product Image Viewer')

    selected_product_name = st.sidebar.selectbox(
        'Select a Product', df['Product Name'].unique())
    filtered_df = df[df['Product Name'] == selected_product_name]

    if not filtered_df.empty:

        # Displays the image of the selected product.
        image_url = filtered_df['Image URL'].iloc[0]
        st.sidebar.image(image_url)

        # Different prices the product is/has been.
        most_recent_price = get_most_recent_price(filtered_df)
        st.sidebar.write(
            f'Current price: £{round(most_recent_price["Price"], 2)}')

        highest_price = get_price_info(filtered_df, False)
        st.sidebar.write(
            f'Highest Price: £{round(highest_price["Price"], 2)}')

        lowest_price = get_price_info(filtered_df, True)
        st.sidebar.write(f'Lowest Price: £{round(lowest_price["Price"], 2)}')

        # Changes the Product Availability from True/False to In Stock/Out of Stock.
        print(most_recent_price["Product Availability"])
        if most_recent_price["Product Availability"] == True:
            st.sidebar.write(
                'Availability: In Stock')
        else:
            st.sidebar.write(
                'Availability: Out of Stock')

        # Button that links to the products URL.
        st.sidebar.link_button(
            "Product Page", most_recent_price["Product URL"])

    else:
        st.sidebar.write("No image available for the selected product.")


def display_admin_main_body(df: DataFrame) -> None:
    """
    Displays all of the admin main body for streamlit.
    """
    sorted_df = df.sort_values(
        by=['Product ID', 'Updated At'], ascending=[True, False])

    most_recent_prices = sorted_df.groupby('Product ID').first()

    # Header metrics
    head_cols = st.columns(3)
    with head_cols[0]:
        st.metric("Total No. of Users :bust_in_silhouette:",
                  df["User Email"].nunique())

    with head_cols[1]:
        st.metric("Total No. of Products", df["Product Name"].nunique())

    with head_cols[2]:
        st.metric("Total No. of Subscriptions",
                  df["Subscription ID"].nunique())

    # Main body of Dashboard
    body_cols = st.columns(2)
    with body_cols[0]:

        name_in_selected_products_price = get_names_of_selected_products(
            most_recent_prices, "most_recent")

        if not name_in_selected_products_price.any():
            st.error("Please select at least one product.")

        else:
            st.altair_chart(get_latest_price_readings(
                most_recent_prices[name_in_selected_products_price]), use_container_width=True)

    with body_cols[1]:
        # Need to be repeated due to the use of a different dataframe.
        name_in_selected_products = get_names_of_selected_products(
            df, "all_admin_pop")

        if not name_in_selected_products.any():
            st.error("Please select at least one product.")
        else:
            st.altair_chart(get_popularity_of_products(df[name_in_selected_products]),
                            use_container_width=True)

    # Repeated in order for the selection bar to look more presentable.
    name_in_selected_products_all = get_names_of_selected_products(
        df, "all_admin")

    st.altair_chart(get_price_of_products_over_time(df[name_in_selected_products_all]),
                    use_container_width=True)


def display_user_admin_info(users: list[dict]) -> None:
    """
    Displays a table showing all user information.
    """

    st.title("User Information:")
    admin_df = pd.DataFrame(users)
    user_information = admin_df.loc[:, admin_df.columns != "password"]
    wanted_user = user_information[["user_id", "first_name",
                                    "last_name", "email"]]
    wanted_user.columns = ["User ID", "First Name", "Last Name", "Email"]

    selected_users = get_multiselect_products(
        DEFAULT_PRODUCT, wanted_user, "admin-user-info", "Email", "Selected Users (by Email)")
    selected_user_emails = wanted_user["Email"].isin(selected_users)

    st.dataframe(wanted_user[selected_user_emails],
                 hide_index=True, use_container_width=True)


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

    display_admin_main_body(df)

    display_user_admin_info(users)

    render_sidebar(df)


def get_multiselect_products(min_default: int, products: DataFrame,
                             key_value: str, value: str,
                             title: str) -> st.multiselect:
    """Returns a multiselect bar that you are able to select product names from."""

    return st.multiselect(title,
                          list(products[value].unique()),
                          default=products[value].unique(
                          )[FIRST_PRODUCT:min_default],
                          placeholder="Please select a product...", key=key_value)


def get_selected_products(products: DataFrame, key_value: str) -> list:
    """
    Returns the selected plants in the sidebar.
    By Default this returns 1 if you have less than 3 products and
    3 if you have more than 3.
    """
    if len(products["Product Name"].unique()) < 3:
        return get_multiselect_products(DEFAULT_MIN, products,
                                        key_value, "Product Name",
                                        "Selected Products")

    return get_multiselect_products(DEFAULT_PRODUCT, products,
                                    key_value, "Product Name",
                                    "Selected Products")


def get_names_of_selected_products(products: DataFrame, key_value: str) -> pd.Series:
    """
    Returns the names of the selected products in the sidebar.
    """
    selected_products_names = get_selected_products(products, key_value)
    return products["Product Name"].isin(selected_products_names)


def display_user_specific_data(df: DataFrame) -> None:
    """
    Creates a user specific display.
    """
    sorted_df = df.sort_values(
        by=['Product ID', 'Updated At'], ascending=[True, False])
    most_recent_prices = sorted_df.groupby('Product ID').first()

    # User Header Metrics
    head_cols = st.columns(2)
    with head_cols[0]:
        st.metric("Total No. of Products", df["Product Name"].nunique())

    with head_cols[1]:
        st.metric("Total Price of Products",
                  f'£{round(most_recent_prices["Price"].astype(float).sum(), 2)}')

    # User latest product price bar chart.
    name_in_selected_products = get_names_of_selected_products(
        most_recent_prices, "recent_user")
    if not name_in_selected_products.any():
        st.error("Please select at least one product.")

    else:
        st.altair_chart(get_latest_price_readings(
            most_recent_prices[name_in_selected_products]), use_container_width=True)

    # User product price over time.
    name_in_selected_products_all = get_names_of_selected_products(
        df, "recent_user_all")
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
    render_sidebar(user_specific_df)
    display_user_specific_data(user_specific_df)


def render_dashboard(df: DataFrame, users: list[dict]) -> None:
    """
    Decides which dashboard to show depending on the type of account logged in.
    """
    if st.session_state.get('user_id') == 0:
        render_admin_dashboard(df, users)
    else:
        render_user_dashboard(df)
