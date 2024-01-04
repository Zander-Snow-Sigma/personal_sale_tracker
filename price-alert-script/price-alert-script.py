"""
Script which compares latest product prices with prior entires and notifies user if price drops.
"""
import logging
from os import environ
from urllib.parse import urlparse
from psycopg2 import connect, extras
from psycopg2.extensions import connection
from datetime import datetime
from decimal import Decimal
from itertools import groupby

from dotenv import load_dotenv
import boto3

logging.basicConfig(filename='price_alert_logs.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


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


def get_prices_of_latest_pair_of_products(
        rds_conn: connection, product_id_of_interest: int) -> list:
    """
    Query RDS prices table for product prices. 
    Returns a list of of dictionaries of the two most recent products in 
    the prices table with the specified ID.
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT * FROM prices WHERE product_id = (%s) ORDER BY updated_at DESC LIMIT 2;",
                (product_id_of_interest,))
    latest_prices = cur.fetchall()
    cur.close()

    latest_prices = [dict(row) for row in latest_prices]
    for row in latest_prices:
        row['updated_at'] = datetime.fromtimestamp(
            row['updated_at'].timestamp()).strftime('%Y-%m-%d %H:%M:%S.%f')
        row['price'] = float(row['price'])

    latest_prices = sorted(latest_prices, key=lambda x: x['product_id'])

    return latest_prices


def compare_latest_two_prices(latest_price_entries: dict) -> bool:
    """
    Compare values of price for last two  entries of each product for that specific ID.
    """

    try:
        if len(latest_price_entries) > 1:
            return latest_price_entries[-2]['price'] < latest_price_entries[-1]['price']

    except UnboundLocalError:
        return False


def get_user_emails(rds_conn: connection) -> list[dict]:
    """
    Query RDS for every instance of a subscription.
    Collects all the relevant information to check if there is a discount:
    user ID, user email, product id, product name, discount status.
    """
    list_of_subscription_instances = []
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT * FROM subscriptions;")
    all_subscriptions = [dict(row) for row in cur.fetchall()]

    for subscription in all_subscriptions:

        user_id = subscription['user_id']
        product_id = subscription['product_id']

        cur.execute("SELECT email FROM users WHERE user_id = (%s);", (user_id,))
        user_email = [dict(row) for row in cur.fetchall()][0]['email']

        cur.execute(
            "SELECT product_name FROM products WHERE product_id = (%s);", (product_id,))
        product_name = [dict(row) for row in cur.fetchall()][0]['product_name']

        is_discounted = compare_latest_two_prices(
            get_prices_of_latest_pair_of_products(rds_conn, product_id))

        list_of_subscription_instances.append({
            'user_id': user_id,
            'user_email': user_email,
            'product_id': product_id,
            'product_name': product_name,
            'is_discounted': is_discounted
        })

    return list_of_subscription_instances


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


def send_email(ses_client, sender, recipient, subject, body) -> None:
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

    logging.info(f"Email sent! Message ID: {response['MessageId']}")


def selectively_send_emails(ses_client, subscription_instances: list[list]):
    """
    Selectively sending emails to users if price drops
    """

    # [TODO]: Work out who the 'sender' should be.
    # [TODO]: Include the value of the discount in a concise, computationally efficient way.
    # [TODO]: Make email prettier.

    sender = 'trainee.tayla.dawson@sigmalabs.co.uk'

    for subscription in subscription_instances:
        if subscription['is_discounted'] == True:
            recipient = 'trainee.tayla.dawson@sigmalabs.co.uk'
            # recipient = subscription['user_email']
            subject = "Your item has decreased in price!"
            body = f"Item {subscription['product_name']} has decreased in price!"
            send_email(ses_client, sender, recipient, subject, body)

        else:
            logging.info(f"Email not sent; no price change.")


if __name__ == "__main__":

    load_dotenv()
    conn = get_database_connection()

    user_product_booleans = get_user_emails(conn)
    ses_client = create_ses_client()
    selectively_send_emails(ses_client, user_product_booleans)
