"""
Script which scrapes webpages and inserts updated price data into prices table in RDS.
Users are updated if their product has gone down in price, or if its stock status
has changed. 
Triggered every three minutes.
"""

import logging
import json
from os import environ
from datetime import datetime

import concurrent.futures
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
            SELECT product_availability FROM products WHERE product_id = %s
            """

EMAIL_QUERY = """
            SELECT users.email FROM users 
            FULL OUTER JOIN subscriptions ON users.user_id = subscriptions.user_id 
            WHERE subscriptions.product_id = %s
            """

INSERT_PRICE_QUERY = """
            INSERT INTO prices (updated_at, product_id, price) VALUES (%s, %s, %s);
            """

GET_ALL_PRODUCTS_QUERY = "SELECT * FROM products;"

GET_LATEST_PRICE_QUERY = """
            SELECT price FROM prices WHERE product_id = (%s) 
            ORDER BY updated_at DESC LIMIT 1;
            """


def get_database_connection() -> connection:
    """
    Return a connection of database.
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
    Query database for data on all products.
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute(GET_ALL_PRODUCTS_QUERY)
    rows = cur.fetchall()
    cur.close()

    new_rows = [dict(row) for row in rows]
    return new_rows


def get_user_data(rds_conn: connection, product_id: int) -> list:
    """
    Query database for users which are subscribed to given product.
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute(EMAIL_QUERY, (product_id,))
    rows = cur.fetchall()
    cur.close()

    return [entry['email'] for entry in rows]


def update_product_availability(rds_conn: connection, product,
                                availability: bool,
                                ses_client: boto3.client) -> None:
    """
    Update product table to reflect availability of item as shown on webpage.
    Emails users about a change in availability. 
    """

    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(UPDATE_AVAILABILITY_QUERY,
                    (availability, product['product_id']))

    rds_conn.commit()

    recipients = get_user_data(rds_conn, product['product_id'])

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
            f"""
            Product {product['product_name']} back in stock. 
            User Notified. Message ID: {response['MessageId']}"""
        )

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
            f"""
            Product {product['product_name']} out of stock. 
            User Notified. Message ID: {response['MessageId']}"""
        )


def check_product_availability(rds_conn: connection, product_id: int) -> bool:
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

    cur.execute(GET_LATEST_PRICE_QUERY,
                (product_id,))
    rows = cur.fetchall()
    cur.close()

    latest_price = [float(entry['price']) for entry in rows if entry['price']]

    if len(latest_price) >= 1:
        return latest_price[0]


def insert_new_price_data(rds_conn: connection,
                          product_id: int, new_price: float) -> None:
    """
    Insert product_id, current product price, and timestamp into prices table in database.
    """
    current_timestamp = datetime.now()

    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(INSERT_PRICE_QUERY,
                    (current_timestamp, product_id, new_price))

    rds_conn.commit()


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
                            old_price: float, new_price: float) -> None:
    """
    Send email to user if product price decreases in price. 
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
            f"""
            Product {product_data['product_name']} price reduced. 
            User notified. Message ID: {response['MessageId']}"""
        )


def scrape_asos_page(rds_conn: connection, item: dict,
                     header: dict, ses_client: boto3.client, page_session) -> None:
    """
    Takes in one item as a dictionary.
    Scrapes webpage and gets the new price.
    Updates the availability of product.
    Emails users if there is a change in availability or a decrease in price.
    """

    page = page_session.get(
        item["product_url"], headers=header, timeout=5)
    soup = BeautifulSoup(page.text, "html.parser").find(
        "script", type="application/ld+json")
    asos_item_json = json.loads(soup.string)

    # Matching to an API entry.
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
    product_id_db = item['product_id']

    # Updating the availability.
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
            # Updating database and alerting users if item now in stock.
            update_product_availability(conn, item, True, ses_client)

        prev_price = get_latest_price_data(rds_conn, product_id_db)
        new_price = new_scraped_price

        if new_price and prev_price and new_price != prev_price:
            # Adding new price to database if it has changed.
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
            update_product_availability(conn, item, False, ses_client)


if __name__ == "__main__":

    load_dotenv()
    EMAIL_SENDER = environ['SENDER_EMAIL_ADDRESS']

    conn = get_database_connection()
    email_client = create_ses_client()
    headers = {'user-agent': environ["USER_AGENT"]}
    products = get_all_product_data(conn)
    # session = requests.Session()

    with concurrent.futures.ThreadPoolExecutor() as multiprocessor:

        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100, pool_maxsize=100)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        def partial_fetch_product_data(item):
            """
            Multiprocessing scrape asos function.
            """
            return scrape_asos_page(conn, item, headers, email_client, session)

        multiprocessor.map(partial_fetch_product_data, products)
