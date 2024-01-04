"""
Script which compares latest product prices with prior entires and notifies user if price drops.
"""


import json
from os import environ
from urllib.parse import urlparse
from psycopg2 import connect, extras
from psycopg2.extensions import connection
from datetime import datetime
from decimal import Decimal
from itertools import groupby

from dotenv import load_dotenv

import boto3


def get_database_connection() -> connection:
    """
    Return a connection our database.
    """
    try:
        return connect(
            user=environ["DB_USER"],
            password=environ["DB_PASSWORD"],
            host=environ["DB_HOST"],
            port=environ["DB_PORT"],
            database=environ["DB_NAME"]
        )
    except ConnectionError as error:
        return error


def get_prices_of_latest_pair_of_products(rds_conn: connection):
    """
    Query RDS products table for all products.
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    # Get number of unique products from product table
    cur.execute("SELECT count(*) FROM products;")
    number_of_products = cur.fetchall()[0]['count']

    # Get prices of last pair of price readings
    # cur.execute("SELECT * FROM prices ORDER BY updated_at ASC LIMIT (%s)",
    #            (number_of_products*2,))
    # [TODO] ^^ this seemed to cut off any products that werent entered in order. Need to resolve this so it does not do this, but
    # can still only access the most recent pairs of products
    cur.execute("SELECT * FROM prices ORDER BY updated_at;")
    latest_prices = cur.fetchall()

    # Separate last prices from second last into two dicts and compare them

    cur.close()

    # converting all to dict
    latest_prices = [dict(row) for row in latest_prices]

    # converting datatypes to readable ones
    for row in latest_prices:
        row['updated_at'] = datetime.fromtimestamp(
            row['updated_at'].timestamp()).strftime('%Y-%m-%d %H:%M:%S.%f')
        row['price'] = float(row['price'])

    # sort the dictionaries so they're paired by product id
    latest_prices = sorted(latest_prices, key=lambda x: x['product_id'])
    grouped_by_product_id = {key: list(group) for key, group in groupby(
        latest_prices, key=lambda x: x['product_id'])}

    return grouped_by_product_id


def compare_latest_two_prices(latest_price_entries: dict, product_id_of_interest: int) -> bool:
    """
    Compare values of price for last two  entries of each product.
    """
    # make function take in product id and return true false for just one product

    # takes in the result of prev function and compares the last two entries for a product
    # outputs bool. If price increases, return true

    for key, value in latest_price_entries.items():
        if key == product_id_of_interest:
            products_of_interest = value
            # this will only return one list because they have all been grouped previously
    # conditions for if the price has increased or stayed same. True if theres an increase.
    if products_of_interest[-1]['price'] < products_of_interest[-2]['price']:
        return True

    else:
        return False
    # condense this ^^


def get_user_emails(rds_conn: connection):
    """
    Query RDS user table for User emails.
    """
    list_of_lists = []
    # ^needs a better name. Holds all the values from the point at the bottom of functn
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    # Find all subscriptions
    cur.execute("SELECT * FROM subscriptions;")
    # makes it a list of dicts
    all_subscriptions = [dict(row) for row in cur.fetchall()]

    for subscription in all_subscriptions:
        user_id = subscription['user_id']
        cur.execute("SELECT email FROM users WHERE user_id = (%s);", (user_id,))
        user_email = [dict(row) for row in cur.fetchall()][0]['email']
        product_id = subscription['product_id']

        # get product name
        cur.execute(
            "SELECT product_name FROM products WHERE product_id = (%s);", (product_id,))
        product_name = [dict(row) for row in cur.fetchall()][0]['product_name']

        is_discounted = compare_latest_two_prices(
            get_prices_of_latest_pair_of_products(rds_conn), product_id)

        list_of_lists.append(
            [user_id, user_email, product_id, product_name, is_discounted])

    # return a dict of the user email, product name/id, true or false for if its been updated

    return list_of_lists  # make this a dict instead? Will me more consistent indexing


def create_ses_client():
    """
    Create and return a Boto3 client for AWS SES using AWS credentials.
    """
    ses_client = boto3.client(
        'ses',
        aws_access_key_id=environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=environ["AWS_SECRET_ACCESS_KEY"],
        region_name="eu-west-2"
    )
    return ses_client


def send_email(ses_client, sender, recipient, subject, body):
    """
    Sends an email with desired subject and body.
    """

    response = ses_client.send_email(
        Source=sender,
        Destination={'ToAddresses': [recipient]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body}}
        }
    )
    # Change print to log statement that gets logged to log file

    print(f"Email sent! Message ID: {response['MessageId']}")


def selectively_send_emails(ses_client, boolean_list: list[list]):
    """Selectively sending emails to users if price drops"""

    # [TODO]: Rename 'boolean list. This refers to the list that comes out of 'get user emails'.
    # [TODO]: Work out who the 'sender' should be
    # [TODO]: Include the value of the discount in a concise, computationally efficient way

    sender = 'trainee.tayla.dawson@sigmalabs.co.uk'

    for subscription in boolean_list:
        if subscription[-1] == True:
            # recipient = 'trainee.tayla.dawson@sigmalabs.co.uk'  # change this to each user
            recipient = subscription[1]
            subject = 'Your item has decreased in price!'
            body = f'Item {subscription[-2]} has decreased in price.'

            send_email(ses_client, sender, recipient, subject, body)
        else:
            print("Email not sent based on the condition.")


if __name__ == "__main__":

    load_dotenv()
    conn = get_database_connection()
    latest_data = get_prices_of_latest_pair_of_products(conn)

    # get_prices_of_latest_pair_of_products(conn)
    user_product_booleans = get_user_emails(conn)

    # compare_latest_two_prices(latest_data, 6)
    ses_client = create_ses_client()
    selectively_send_emails(ses_client, user_product_booleans)
