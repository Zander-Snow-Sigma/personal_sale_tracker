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
    # try:
    #     return connect(
    #         user=environ["DB_USER"],
    #         password=environ["DB_PASSWORD"],
    #         host=environ["DB_HOST"],
    #         port=environ["DB_PORT"],
    #         database=environ["DB_NAME"]
    #     )
    # except ConnectionError as error:
    #     return error

    return connect("dbname=sale_tracker user=harvindgrewal host=localhost")


def get_latest_products():
    """Query RDS products table for all products"""

    conn = get_database_connection()

    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT * FROM product;")
    rows = cur.fetchall()
    print(rows)

    conn.close()

    pass


def get_latest_prices():
    """Query RDS prices table for latest prices of all products"""
    pass


def get_second_latest_prices():
    """Query RDS prices table for second latest prices of all products"""
    pass


def compare_latest_two_prices():
    """Compare values of price for last two  entries of each product"""
    pass


def get_user_emails():
    """Query RDS user table for User emails"""
    pass


def send_emails():
    """If price of product drops, send user email"""
    pass


if __name__ == "__main__":

    load_dotenv()
