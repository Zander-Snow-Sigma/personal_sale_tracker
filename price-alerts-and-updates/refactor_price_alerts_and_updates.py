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

EMAIL_QUERY = """
            SELECT users.email FROM users 
            FULL OUTER JOIN subscriptions ON users.user_id = subscriptions.user_id 
            WHERE subscriptions.product_id = %s
            """

INSERT_PRICE_QUERY = """
            INSERT INTO prices (updated_at, product_id, price) 
            VALUES %s
            """

EMAIL_SENDER = "trainee.tayla.dawson@sigmalabs.co.uk"

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


def get_user_data(rds_conn: connection, product_id: int):
    """
    Query database for users which are subscribed to given product
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute(EMAIL_QUERY, (product_id,))
    rows = cur.fetchall()
    cur.close()

    return [entry['email'] for entry in rows]


def update_product_availability(rds_conn: connection, product, availability: bool, ses_client: boto3.client):
    """
    Update product table to reflect availability of item as shown on webpage.
    Emails users about a change in availability. 
    """

    # Update database with new stock info
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(UPDATE_AVAILABILITY_QUERY,
                    (availability, product['product_id']))

    rds_conn.commit()

    # gets users that are subscribed to that product as list
    # empty list if product id has no subscribers
    recipients = get_user_data(rds_conn, product['product_id'])

    # back in stock, only send email if there are subs
    if availability == True and len(recipients) >= 1:
        for recipient in recipients:
            response = ses_client.send_email(
                Source=EMAIL_SENDER,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': "Update of product availability"},
                    'Body': {'Html': {'Data': f"""<meta charset="UTF-8">
                                <center>
                                <h1 font-family="Ariel">
                                Your item <a href={product['product_url']}>
                                {product['product_name']}</a> is now back in stock!
                                </h1>
                                <br></br>
                                <img src="{product["image_url"]}" alt="img">
                                </center>"""
                                      }}
                }
            )
        logging.info(
            f"Product {product['product_name']} back in stock. User Notified. Message ID: {response['MessageId']}")

    # out of stock, only send email if there are subs
    elif availability == False and len(recipients) >= 1:
        for recipient in recipients:
            response = ses_client.send_email(
                Source=EMAIL_SENDER,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': "Update of product availability"},
                    'Body': {'Html': {'Data': f"""<meta charset="UTF-8">
                                <center>
                                <h1 font-family="Ariel">
                                Your item <a href={product['product_url']}>
                                {product['product_name']}</a> is out of stock!
                                </h1>
                                <br></br>
                                <img src="{product["image_url"]}" alt="img">
                                </center>"""
                                      }}
                }
            )
        logging.info(
            f"Product {product['product_name']} out of stock. User Notified. Message ID: {response['MessageId']}")


def check_product_availability(rds_conn: connection, product_id: int):
    """
    Checks what the current product availability is
    """
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(CHECK_AVAILABILITY_QUERY,
                    (product_id,))
        return cur.fetchone()['product_availability']


def get_latest_price_data(rds_conn: connection, product_id: dict) -> float:
    """
    Gets latest price from database.
    """

    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT price FROM prices WHERE product_id = (%s) ORDER BY updated_at DESC LIMIT 1;",
                (product_id,))
    rows = cur.fetchall()
    cur.close()

    latest_price = [float(entry['price']) for entry in rows if entry['price']]

    # TODO: Properly handle when there is no price for a given product - MAKE SURE THEY'RE SEEDED WITH ONE UPON ENTRY

    if len(latest_price) >= 1:
        return latest_price[0]  # float of latest price for given product id


def insert_new_price_data(rds_conn: connection, product_id: int, new_price: float):
    """
    Insert product_id, current product price and timestamp into prices table in database.
    """
    current_timestamp = datetime.now()
    product_id = str(product_id)
    new_price = str(new_price)

    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        # cur.execute(
        #     "INSERT INTO prices (updated_at, product_id, price) VALUES %s;",
        #     ((current_timestamp, product_id, new_price)))
        cur.execute(
            f"INSERT INTO prices (updated_at, product_id, price) VALUES (CURRENT_TIMESTAMP, {product_id}, {new_price});")

    rds_conn.commit()


# [TODO] Check the current timestamp works and is readable by database. Make secure

def get_discount_amount(previous_price: float, new_price: float) -> dict:
    """
    Gets the old and new product price. 
    Calculates the percentage discount. 
    """
    if previous_price and new_price:

        discount_value = previous_price - new_price
        fractional_discount = discount_value/previous_price
        percentage_discount = fractional_discount * 100

        return {'previous_price': previous_price,
                'new_price': new_price,
                'percentage_discount': percentage_discount}

    return {'previous_price': 'Could not extract.',
            'new_price': 'Could not extract.',
            'percentage_discount': 'Unknown'}


def send_price_update_email(ses_client: boto3.client,
                            product_data: dict, recipients: list,
                            old_price: float, new_price: float):
    """
    Send email to user if product price changes
    """

    discount = get_discount_amount(old_price, new_price)

    sender = EMAIL_SENDER

    for recipient in recipients:
        response = ses_client.send_email(
            Source=sender,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': "Your item has decreased in price!"},
                'Body': {'Html': {'Data': f"""<meta charset="UTF-8">
                            <center>
                            <h1 font-family="Ariel">
                            Your item <a href={product_data['product_url']}>
                            {product_data['product_name']}</a> has gone down 
                            by {discount['percentage_discount']:.1f}%
                            </h1>
                            <body class="New price" font-family="Ariel">
                            <b>
                            New price = £{discount['new_price']:.2f}
                            </body><br></br>
                            <body class="Previous price" font-family="Ariel">
                            <b>Previous price = £{discount['previous_price']:.2f}
                            </b>
                            </body><br></br>
                            <img src="{product_data["image_url"]}" alt="img">
                            </center>"""}}
            }
        )
        logging.info(
            f"Product {product_data['product_name']} price reduced. User notified. Message ID: {response['MessageId']}")


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
                # updates db and alerts users if now in stock
                update_product_availability(conn, item, True, ses_client)

            # compare old and new price
            prev_price = get_latest_price_data(rds_conn, product_id_db)
            new_price = new_scraped_price

            print(new_price, prev_price)

            if new_price and prev_price and new_price != prev_price:
                # add new price to database if it has changed
                insert_new_price_data(
                    rds_conn, product_id_db, new_scraped_price)

                if new_price < prev_price:
                    recipients = get_user_data(rds_conn, product_id_db)
                    if len(recipients) >= 1:
                        send_price_update_email(
                            ses_client, item, recipients, prev_price, new_price)

        else:
            asos_item_json["is_in_stock"] = False
            prev_availability = check_product_availability(
                rds_conn, product_id_db)

            if prev_availability != False:
                # updates db and alerts users if now out of stock
                update_product_availability(conn, item, False, ses_client)


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
    email_client = create_ses_client()
    headers = {'user-agent': environ["USER_AGENT"]}
    products = get_all_product_data(conn)
    session = requests.Session()
    # asos_data = scrape_asos_page(
    #     conn, products, headers, email_client, session)

    # asos_data
    scrape_asos_page(conn, products, headers, email_client, session)
