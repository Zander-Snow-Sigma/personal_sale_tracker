"""
Script which scrapes webpages and inserts updated price data into prices table in RDS
Triggered every three minutes
If URL invalid, unsubscribe user from produce and send user notification
"""

# [TODO]: Handle initial entries into prices table
# [TODO]: Go through ALL subscriptions in the table

import logging
import json
from os import environ
import time

from datetime import datetime
import requests
import boto3
from psycopg2 import connect, extras
from psycopg2.extensions import connection
from bs4 import BeautifulSoup
from dotenv import load_dotenv

logging.basicConfig(filename='price_alert_logs.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

STARTER_ASOS_API = "https://www.asos.com/api/product/catalogue/v3/stockprice?"

UPDATE_AVAILABILITY_QUERY = """
            UPDATE products 
            SET product_availability = %s
            WHERE product_id = %s
            """

CHECK_AVAILABILITY_QUERY = """
            SELECT product_availability FROM products WHERE product_id = %s"""

# SHARED FUNCTIONS ______________________________________________________________


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


def create_ses_client() -> boto3.client:
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

# ONLY needed to update the database IF there is a change to the product


def get_all_product_data(rds_conn: connection) -> extras.RealDictRow:
    """
    Query database for data on all products that price data is required for
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)
    # Get all unique products from product table
    cur.execute("SELECT * FROM products;")
    rows = cur.fetchall()
    cur.close()

    # return rows
    new_rows = [dict(row) for row in rows]
    return new_rows  # A list of dictionaries of each product

# UPDATING THE DATABASE______________________________________________________________

# Scrape ASOS for latest info on price and availability


def update_product_availability(rds_conn: connection, product, availability: bool):
    """
    Update product table to reflect availability of item as shown on webpage.
    Emails users about a change in availability. 
    """

    # [TODO]: incorporate emails (either out of stock, or back in stock)
    # because it is only called if the stock status changes
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(UPDATE_AVAILABILITY_QUERY,
                    (availability, product['product_id']))

    rds_conn.commit()


def check_product_availability(rds_conn: connection, product_id: int):
    """
    Checks what the current product availability is
    """
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(CHECK_AVAILABILITY_QUERY,
                    (product_id,))
        return cur.fetchone()['product_availability']


def scrape_asos_page(rds_conn: connection, item_in_database: dict, header: dict, ses_client: boto3.client, session) -> tuple:
    """
    Scrapes an ASOS page to UPDATE DATABASE IF THERE IS A CHANGE IN PRICE.
    """
    # gets all the items and their ids, which have been provided from database
    for item in item_in_database:  # goes through the list of dicts from get_products

        page = session.get(
            item["product_url"], headers=header, timeout=5)
        soup = BeautifulSoup(page.text, "html.parser").find(
            "script", type="application/ld+json")
        asos_item_json = json.loads(soup.string)

        # matches to an API entry
        if "productID" in asos_item_json.keys():
            price_endpoint = f"""{STARTER_ASOS_API}productIds={
                asos_item_json['productID']
                }&store=COM&currency=GBP"""
        else:
            price_endpoint = f"""{STARTER_ASOS_API}productIds={
                asos_item_json['@graph'][0]['productID']
                }&store=COM&currency=GBP"""

        product_api_result = requests.get(price_endpoint, timeout=5).json()

        # new price and current product id
        new_scraped_price = product_api_result[0]["productPrice"]["current"]["value"]
        product_id_db = item['product_id']

        # updating the availability
        # to make it less complicated, its just going to update the availability every time for now
        sizes = product_api_result[0]['variants']
        availabilities = []
        for size in sizes:
            if size["isInStock"] == True:
                availabilities.append(size["isInStock"])
            else:
                availabilities.append(size["isInStock"])

        if True in availabilities:
            asos_item_json["is_in_stock"] = True
            prev_availability = check_product_availability(
                rds_conn, product_id_db)

            if prev_availability != True:
                update_product_availability(conn, item, True)
                # and alert users that its back in stock - call inside update product availability

            # THEN
            # check if price has changed
            # update prices table if it has changed
            # send email to users letting them know of price has decreased (use prev alert function)

        else:
            asos_item_json["is_in_stock"] = False
            prev_availability = check_product_availability(
                rds_conn, product_id_db)

            if prev_availability != False:
                update_product_availability(conn, item, False)
                # and email users to let them know it is now out of stock - call inside update product availability

        # return product_api_result
        # print(product_api_result, "*************")
        # print(new_scraped_price, "**", product_id_db, )


# SENDING EMAILS______________________________________________________________

# [TODO] A function that finds all user info (user id --> email) from subscriptions for a given product id
                # Query subscriptions table for all subs with that product id
                # for each of those user ids, query the user table for their emails
                # store these emails in a list
                # send price alert email to each of them
                # embed this function in the asos scraper function

if __name__ == "__main__":

    load_dotenv()

    conn = get_database_connection()
    # email_client = create_ses_client()
    # headers = {'user-agent': environ["USER_AGENT"]}
    # products = get_all_product_data(conn)

    # session = requests.Session()
    # asos_data = scrape_asos_page(
    #     conn, products, headers, email_client, session)

    # asos_data

    print(check_product_availability(conn, 2))
