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

CURRENT_DATETIME = datetime.now()

STARTER_ASOS_API = "https://www.asos.com/api/product/catalogue/v3/stockprice?"
EMAIL_QUERY = """
            SELECT users.email FROM users 
            FULL OUTER JOIN subscriptions ON users.user_id = subscriptions.user_id 
            WHERE subscriptions.product_id = %s
            """
UPDATE_AVAILABILITY_QUERY = """
            UPDATE products 
            SET product_availability = %s
            WHERE product_id = %s
            """
INSERT_PRICE_QUERY = """
            INSERT INTO prices (updated_at, product_id, price) 
            VALUES %s
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


def get_user_data(rds_conn: connection, product_id: int):
    """
    Query database for users which are subscribed to given product
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute(EMAIL_QUERY, (product_id,))
    rows = cur.fetchall()
    cur.close()

    return [entry['email'] for entry in rows]


def get_latest_price_data(rds_conn: connection, product: dict) -> float:
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT price FROM prices WHERE product_id = (%s) ORDER BY updated_at DESC LIMIT 1;",
                (product['product_id'],))
    rows = cur.fetchall()
    cur.close()

    latest_price = [entry['price'] for entry in rows if entry['price']]

    return (latest_price)


def update_product_availability(rds_conn: connection, product, availability: bool):
    """
    Update product table to reflect availability of item as shown on webpage
    """
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(UPDATE_AVAILABILITY_QUERY,
                    (availability, product['product_id']))

    rds_conn.commit()


def insert_new_price_data(rds_conn: connection, product_data: dict):
    """
    Insert product_id, current product price and timestamp into prices table in database
    """
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        extras.execute_values(cur, INSERT_PRICE_QUERY, product_data)

    rds_conn.commit()


def get_product_discount(rds_conn: connection, new_price: float, product: dict) -> dict:
    """
    Calculate discount percentage based on new and old prices
    """
    discount_stats = {}

    discount_stats['new_price'] = float(new_price)
    discount_stats['previous_price'] = float(
        get_latest_price_data(rds_conn, product))

    discount_value = discount_stats['previous_price'] - \
        discount_stats['new_price']
    fractional_discount = discount_value/discount_stats['previous_price']

    discount_stats['percentage_discount'] = fractional_discount * 100

    return discount_stats


def send_stock_update_email(rds_conn: connection, ses_client: boto3.client, product_data: dict, back_in_stock: bool):
    """
    Set sender, recipient and condition for email
    """
    sender = environ['SENDER']
    recipients = get_user_data(rds_conn, product_data['product_id'])

    if back_in_stock:
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
        logging.info(
            f"Product {product_data['product_name']} back in stock. User Notified. Message ID: {response['MessageId']}")

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
        logging.info(
            f"Product {product_data['product_name']} out of stock. User Notified. Message ID: {response['MessageId']}")


def send_price_update_email(rds_conn: connection, ses_client: boto3.client, product_data: dict, price: float):
    """
    Send email to user if product price changes
    """

    discount = get_product_discount(rds_conn, price, product_data)

    sender = environ['SENDER']
    recipients = get_user_data(rds_conn, product_data['product_id'])

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
    Scrapes an ASOS page and returns the price of selected product.
    If price not found, remove product from tracking and notify user
    """

    page = session.get(
        item_in_database["product_url"], headers=header, timeout=5)
    soup = BeautifulSoup(page.text, "html.parser").find(
        "script", type="application/ld+json")
    asos_item_json = json.loads(soup.string)

    if "productID" in asos_item_json.keys():
        price_endpoint = f"""{STARTER_ASOS_API}productIds={
            asos_item_json['productID']
            }&store=COM&currency=GBP"""
    else:
        price_endpoint = f"""{STARTER_ASOS_API}productIds={
            asos_item_json['@graph'][0]['productID']
            }&store=COM&currency=GBP"""

    product_api_result = requests.get(price_endpoint, timeout=5).json()

    new_scraped_price = product_api_result[0]["productPrice"]["current"]["value"]
    sizes = product_api_result[0]['variants']

    latest_recorded_price = get_latest_price_data(rds_conn, item_in_database)

    availabilities = []
    for size in sizes:
        if size["isInStock"] == True:
            availabilities.append(size["isInStock"])
        else:
            availabilities.append(size["isInStock"])

    if True in availabilities:
        asos_item_json["is_in_stock"] = True
    else:
        asos_item_json["is_in_stock"] = False

    # Check if ASOS lists product in stock
    if asos_item_json["is_in_stock"] == True:
        # Check if RDS lists product in stock
        if item_in_database["product_availability"] == True:
            # Check if price has dropped

            if latest_recorded_price:
                if new_scraped_price < float(latest_recorded_price[0]):
                    print("price reduction, "+new_scraped_price,
                          float(latest_recorded_price[0]))

                    send_price_update_email(
                        rds_conn, ses_client, item_in_database, new_scraped_price)

                    return (CURRENT_DATETIME, item_in_database["product_id"], new_scraped_price)
                return (CURRENT_DATETIME, item_in_database["product_id"], 0)
            else:
                return (CURRENT_DATETIME, item_in_database["product_id"], new_scraped_price)

        else:
            update_product_availability(rds_conn, item_in_database, True)
            send_stock_update_email(
                rds_conn, ses_client, item_in_database, True)

            if latest_recorded_price:
                if new_scraped_price < float(latest_recorded_price[0]):
                    send_price_update_email(
                        rds_conn, ses_client, item_in_database, new_scraped_price)

                    return (CURRENT_DATETIME, item_in_database["product_id"], new_scraped_price)
                return (CURRENT_DATETIME, item_in_database["product_id"], 0)
            else:
                return (CURRENT_DATETIME, item_in_database["product_id"], new_scraped_price)
    else:
        if item_in_database["product_availability"] == False:
            return (CURRENT_DATETIME, item_in_database["product_id"], 0)
        else:
            update_product_availability(rds_conn, item_in_database, False)
            send_stock_update_email(
                rds_conn, ses_client, item_in_database, False)
            return (CURRENT_DATETIME, item_in_database["product_id"], 0)


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
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100, pool_maxsize=100)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        def partial_fetch_product_data(item):
            return scrape_asos_page(conn, item, headers, email_client, session)

        product_price_data = list(multiprocessor.map(
            partial_fetch_product_data, products))

    filtered_price_data = [
        entry for entry in product_price_data if entry[-1] != 0.0]

    # insert_new_price_data(conn, filtered_price_data)

    # get the total execution time
    et = time.time()
    elapsed_time = et - st
    print('Execution time:', elapsed_time, 'seconds')
