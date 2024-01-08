"""
Functions to visualise data on streamlit.
"""
from os import environ

import altair as alt
from dotenv import load_dotenv
import pandas as pd
from pandas import DataFrame
import streamlit as st


from database import get_database_connection, get_user_info


def get_latest_price_readings(latest_data: DataFrame) -> alt.vegalite.v5.api.Chart:
    """
    Returns an altair bar chart that shows the latest price readings for each product.
    """

    latest_data["Price (£)"] = latest_data["Price"].astype(float)

    latest_data = latest_data[["Product Name", "Price (£)"]]
    print(latest_data)

    latest_price_readings = alt.Chart(latest_data).mark_bar().encode(
        y=alt.Y('Product Name:N'),
        x=alt.X('Price (£):Q'),
        tooltip=['Product Name:N', 'Price (£):Q'],
        color=alt.Color('Product Name:N', legend=None).scale(scheme='blues')
    ).properties(
        title='Latest Price of Products',
        width=600
    )
    return latest_price_readings
