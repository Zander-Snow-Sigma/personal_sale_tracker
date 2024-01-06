
import pandas as pd
from pandas import DataFrame
import streamlit as st


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
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    return email, password


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
    else:
        st.sidebar.write("No image available for the selected product.")


def display_admin_main_body(df: DataFrame) -> None:
    head_cols = st.columns(3)

    with head_cols[0]:
        st.metric("Total No. of Users :bust_in_silhouette:",
                  df["User Email"].nunique())
    with head_cols[1]:
        st.metric("Total No. of Products", df["Product Name"].nunique())

    with head_cols[2]:
        st.metric("Total No. of Subscriptions",
                  df["Subscription ID"].nunique())


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
    st.table(admin_df.loc[:, admin_df.columns != "password"])
    render_product_image_viewer(df)


def display_user_specific_data(df: DataFrame) -> None:
    """
    Creates a user specific display.
    """
    sorted_df = df.sort_values(
        by=['Product ID', 'Updated At'], ascending=[True, False])
    most_recent_prices = sorted_df.groupby('Product ID').first()
    st.write(f"Dashboard for User ID {st.session_state['user_id']}")
    st.table(most_recent_prices)


def render_user_dashboard(df: DataFrame) -> None:
    """
    Creates the user dashboard in which each user will only be able to
    see information relevant to them.
    """
    user_specific_df = df[df['User ID'] == st.session_state['user_id']]
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
