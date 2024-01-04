"""
Script which compares latest product prices with prior entires and notifies user if price drops
"""


import json
from os import environ
from urllib.parse import urlparse
from psycopg2 import connect, extras
from psycopg2.extensions import connection

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
    """Query RDS products table for all products"""

    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    # Get number of unique products from product table
    cur.execute("SELECT count(*) FROM products;")
    number_of_products = cur.fetchall()[0]['count']

    # Get prices of last pair of price readings
    cur.execute("SELECT * FROM prices ORDER BY updated_at ASC LIMIT (%s)",
                (number_of_products*2,))
    latest_prices = cur.fetchall()

    # Separate last prices from second last into two dicts and compare them

    cur.close()

    return latest_prices


def compare_latest_two_prices():
    """Compare values of price for last two  entries of each product"""
    pass


def get_user_emails(rds_conn: connection):
    """Query RDS user table for User emails"""
    pass


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


def selectively_send_emails(ses_client):
    """Selectively sending emails to users if price drops"""

    sender = 'trainee.harvind.grewal@sigmalabs.co.uk'
    recipient = 'trainee.harvind.grewal@sigmalabs.co.uk'
    subject = 'Test email'
    body = 'Body of email'

    # Your condition for selective sending
    should_send_email = True  # Replace with your own condition

    if should_send_email:
        send_email(ses_client, sender, recipient, subject, body)
    else:
        print("Email not sent based on the condition.")


if __name__ == "__main__":

    load_dotenv()
    conn = get_database_connection()
    print(get_prices_of_latest_pair_of_products(conn))
    ses_client = create_ses_client()

    selectively_send_emails(ses_client)
