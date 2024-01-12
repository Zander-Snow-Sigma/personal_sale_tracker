"""
Functions to visualise data on streamlit.
"""

from datetime import datetime

import altair as alt
import pandas as pd
from pandas import DataFrame

NUM_COLUMNS_LEGEND = 3
MAX_WIDTH = 600
MAX_HEIGHT = 400


def get_latest_price_readings(latest_data: DataFrame) -> alt.vegalite.v5.api.Chart:
    """
    Returns an altair bar chart that shows the latest price readings for each product.
    """

    latest_data["Price (£)"] = latest_data["Price"].astype(float)

    latest_data = latest_data[["Product Name", "Price (£)"]]

    latest_price_readings = alt.Chart(latest_data).mark_bar().encode(
        y=alt.Y('Product Name:N'),
        x=alt.X('Price (£):Q'),
        tooltip=['Product Name:N', 'Price (£):Q'],
        color=alt.Color('Product Name:N', legend=None).scale(scheme='blues')
    ).properties(
        title='Latest Price of Products',
        width=MAX_WIDTH
    )
    return latest_price_readings


def get_popularity_of_products(df: DataFrame) -> alt.vegalite.v5.api.Chart:
    """
    Displays the popularity (number of subscriptions each product has) over time.
    """
    grouped = df.groupby('Product Name')

    product_popularity = grouped['Subscription ID'].nunique()
    product_popularity = product_popularity.reset_index()
    product_popularity.columns = ['Product Name', 'Popularity']

    popularity = alt.Chart(product_popularity).mark_bar().encode(
        y=alt.Y('Product Name:N'),
        x=alt.X('Popularity:Q'),
        tooltip=['Product Name:N', 'Popularity:Q'],
        color=alt.Color('Product Name:N', legend=None).scale(scheme='blues')
    ).properties(
        title='Product Popularity',
        width=MAX_WIDTH
    )
    return popularity


def get_price_of_products_over_time(df: DataFrame) -> alt.vegalite.v5.api.Chart:
    """
    Displays the price of all products over time in a line graph.
    """
    df['Updated At'] = pd.to_datetime(df['Updated At'])

    df['Price'] = df['Price'].astype(float)

    ext = df.sort_values('Updated At').groupby('Product ID').tail(1)
    ext_date = ext['Updated At']
    ext_date = ext_date.apply(lambda x: datetime.now())
    ext['Updated At'] = ext_date

    df = pd.concat([df, ext])

    line_chart = alt.Chart(df).mark_line(interpolate="step").encode(
        x=alt.X('Updated At:T', axis=alt.Axis(title='Time')),
        y=alt.Y('Price:Q', axis=alt.Axis(title='Price')),
        color=alt.Color('Product Name:N', legend=alt.Legend(
            orient='bottom', columns=NUM_COLUMNS_LEGEND)),
        tooltip=['Product Name:N', 'Price:Q', 'Updated At:T']
    ).properties(
        title='Price Over Time by Product',
        width=MAX_WIDTH,
        height=MAX_HEIGHT
    )

    return line_chart
