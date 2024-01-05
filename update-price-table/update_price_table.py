"""
Script which scrapes webpages and inserts updated price data into prices table in RDS
Triggered every three minutes
If URL invalid, unsubscribe user from produce and send user notification
"""
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

import concurrent.futures

logging.basicConfig(filename='price_alert_logs.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


STARTER_ASOS_API = "https://www.asos.com/api/product/catalogue/v3/stockprice?"
EMAIL_QUERY = """
            SELECT users.email FROM users 
            FULL OUTER JOIN subscriptions ON users.user_id = subscriptions.user_id 
            WHERE subscriptions.product_id = %s
            """
INSERT_PRICE_QUERY = """
            INSERT INTO prices (updated_at, product_id, price) 
            VALUES %s
            """
UPDATE_AVAILABILITY_QUERY = """
            UPDATE products 
            SET product_availability = %s
            WHERE product_id = %s
            """


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


def get_all_product_data(rds_conn: connection) -> extras.RealDictRow:
    """
    Query database for data on all products that price data is required for
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)
    # Get all unique products from product table
    cur.execute("SELECT * FROM products;")
    rows = cur.fetchall()
    cur.close()

    return rows


def scrape_asos_page(rds_conn: connection, product: dict, header: dict, ses_client: boto3.client, session) -> float:
    """
    Scrapes an ASOS page and returns the price of selected product.
    If price not found, remove product from tracking and notify user
    """
    current_datetime = datetime.now()
    page = session.get(product["product_url"], headers=header, timeout=5)
    soup = BeautifulSoup(page.text, "html.parser").find(
        "script", type="application/ld+json")

    product_data = json.loads(soup.string)

    if "productID" in product_data.keys():
        price_endpoint = f"""{STARTER_ASOS_API}productIds={
            product_data['productID']
            }&store=COM&currency=GBP"""
    else:
        price_endpoint = f"""{STARTER_ASOS_API}productIds={
            product_data['@graph'][0]['productID']
            }&store=COM&currency=GBP"""

    price = requests.get(price_endpoint, timeout=5).json()[
        0]["productPrice"]["current"]["value"]

    sizes = requests.get(price_endpoint, timeout=5).json()[0]['variants']

    availabilities = []
    for size in sizes:
        if size["isInStock"] == True:
            availabilities.append(size["isInStock"])
        else:
            availabilities.append(size["isInStock"])

    if True in availabilities:
        product_data["is_in_stock"] = True
    else:
        product_data["is_in_stock"] = False

    if product_data["is_in_stock"] == True:

        if product["product_availability"] == True:
            return (current_datetime, product["product_id"], price)

        else:
            update_product_availability(rds_conn, product, True)
            # Send email to notify user of updated subscription status
            send_stock_update_email(rds_conn, ses_client, product, True)
            logging.info(
                f"Product {product['product_name']} back in stock. User Notified")
            return (current_datetime, product["product_id"], price)

    if product_data["is_in_stock"] == False:

        if product["product_availability"] == False:
            return (current_datetime, product["product_id"], 0)

        else:
            update_product_availability(rds_conn, product, False)
            # Send email to notify user of updated subscription status
            send_stock_update_email(rds_conn, ses_client, product, False)
            logging.info(
                f"Product {product['product_name']} out of stock. User Notified")

            return (current_datetime, product["product_id"], 0)


def update_product_availability(rds_conn: connection, product, availability: bool):
    """
    Update product table to reflect availability of item as shown on webpage
    """
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(UPDATE_AVAILABILITY_QUERY,
                    (availability, product['product_id']))

    rds_conn.commit()
    pass


def insert_price_data(rds_conn: connection, product_data: dict):
    """
    Insert product_id, current product price and timestamp into prices table in database
    """
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        extras.execute_values(cur, INSERT_PRICE_QUERY, product_data)

    rds_conn.commit()


def get_user_emails(rds_conn: connection, product_id: int):
    """
    Query database for users which are subscribed to given product
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute(EMAIL_QUERY, (product_id,))
    rows = cur.fetchall()
    cur.close()

    return [entry['email'] for entry in rows]


def send_stock_update_email(rds_conn: connection, ses_client: boto3.client, product_data: dict, availability: bool):
    """
    Set sender, recipient and condition for email
    """
    sender = environ['SENDER']
    recipients = get_user_emails(rds_conn, product_data['product_id'])

    if availability:
        for recipient in recipients:
            response = ses_client.send_email(
                Source=sender,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': "Update of product availability"},
                    'Body': {'Html': {'Data': f"""<meta charset="UTF-8">
                                <center>
                                <h1 font-family="Ariel">
                                Your item <a href={product_data['product_url']}>
                                {product_data['product_name']}</a> is now back in stock!
                                </h1>
                                <br></br>
                                <img src="{product_data["image_url"]}" alt="img">
                                </center>"""
                                      }}
                }
            )

    else:
        for recipient in recipients:
            response = ses_client.send_email(
                Source=sender,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': "Update of product availability"},
                    'Body': {'Html': {'Data': f"""<meta charset="UTF-8">
                                <center>
                                <h1 font-family="Ariel">
                                Your item <a href={product_data['product_url']}>
                                {product_data['product_name']}</a> is out of stock!
                                </h1>
                                <br></br>
                                <img src="{product_data["image_url"]}" alt="img">
                                </center>"""
                                      }}
                }
            )


if __name__ == "__main__":

    # get the start time
    st = time.time()

    load_dotenv()
    conn = get_database_connection()
    email_client = create_ses_client()

    headers = {'user-agent': environ["USER_AGENT"]}

    products = get_all_product_data(conn)

    product_price_data = []

    with concurrent.futures.ThreadPoolExecutor() as multiprocessor:
        session = requests.Session()

        def partial_fetch_product_data(item):
            return scrape_asos_page(conn, item, headers, email_client, session)

        product_price_data = list(multiprocessor.map(
            partial_fetch_product_data, products))

    filtered_price_data = [
        entry for entry in product_price_data if entry[-1] != 0.0]
    insert_price_data(conn, filtered_price_data)

    # get the total execution time
    et = time.time()
    elapsed_time = et - st
    print('Execution time:', elapsed_time, 'seconds')
