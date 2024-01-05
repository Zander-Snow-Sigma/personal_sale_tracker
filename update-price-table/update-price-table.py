"""
Script which scrapes webpages and inserts updated price data into prices table in RDS
Triggered every three minutes
If URL invalid, unsubscribe user from produce and send user notification

[ToDo] - Set email sender and Set Email HTML formatting
- update price extract to match abbeys
- update email formatting to match taylas
"""

import json
from os import environ

import requests
import boto3
from datetime import datetime
from psycopg2 import connect, extras
from psycopg2.extensions import connection
from bs4 import BeautifulSoup
from dotenv import load_dotenv


STARTER_ASOS_API = "https://www.asos.com/api/product/catalogue/v3/stockprice?"

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


def create_ses_client()->boto3.client:
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


def get_all_product_data(rds_conn:connection)->extras.RealDictRow:
    """
    Query database for data on all products that price data is required for
    """

    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    # Get all unique products from product table
    cur.execute("SELECT * FROM products;")
    rows = cur.fetchall()
    cur.close()
  
    return rows

### Update to match Abbeys extract function
def scrape_asos_page(rds_conn:connection, product: dict, header: dict, ses_client:boto3.client) -> float:
    """
    Scrapes an ASOS page and returns the price of selected product.
    If price not found, remove product from tracking and notify user
    """
    page = requests.get(product["product_url"], headers=header, timeout=5)
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

    if price:
        if product['product_availability'] == True:
            return price
        
        elif product['product_availability'] == False:
            update_product_availability(rds_conn, product, True)
            # Send email to notify user of updated subscription status
            send_stock_update_email(rds_conn, ses_client, product, True)
            return price
        
    else:

        if product['product_availability'] == True:
            update_product_availability(rds_conn, product, False)
            # Send email to notify user of updated subscription status
            send_stock_update_email(rds_conn, ses_client, product, False)
            return 0
        
        elif product['product_availability'] == False:
            return 0


def update_product_availability(rds_conn:connection, product, availability:bool):
    """
    Update product table to reflect availability of item as shown on webpage
    """
    
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE products 
            SET product_availability = %s
            WHERE product_id = %s
            """,(availability, product['product_id']))
        
    rds_conn.commit()    
    pass


def insert_price_data(rds_conn: connection, product_data:dict):
    """
    Insert product_id, current product price and timestamp into prices table in database
    """
    
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        extras.execute_values(cur,
            """
            INSERT INTO prices (updated_at, product_id, price) 
            VALUES %s""",
            product_data)
        
    rds_conn.commit()    


def get_user_emails(rds_conn:connection, product_id:int):
    """
    Query database for users which are subscribed to given product
    """

    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("""
                SELECT users.email FROM users 
                FULL OUTER JOIN subscriptions ON users.user_id = subscriptions.user_id 
                WHERE subscriptions.product_id = %s
                """,(product_id,))
    rows = cur.fetchall()
    cur.close()
    
    matching_emails = []
    for entry in rows:
        matching_emails.append(entry['email'])
    
    return matching_emails


def send_stock_update_email(rds_conn:connection, ses_client:boto3.client, product_data:dict, availability:bool):
    """
    Set sender, recipient and condition for email
    """

    sender = 'trainee.harvind.grewal@sigmalabs.co.uk'
    recipients = get_user_emails(rds_conn, product_data['product_id'])
    
    if availability:
        for recipient in recipients:
            response = ses_client.send_email(
                Source=sender,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': "Update of product availability"},
                    'Body': {'Text': {'Data': f"""
                                    The product ({product_data['product_name']}) you have been tracking is now back in stock! 
                                    ({product_data['product_url']}).
                                    """}}
                }
            )
        print(f"Email sent! Message ID: {response['MessageId']}")

    else:
        for recipient in recipients:
            response = ses_client.send_email(
                Source=sender,
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': "Update of product availability"},
                    'Body': {'Text': {'Data': f"""
                                    The product ({product_data['product_name']}) you have been tracking is out of stock! 
                                    ({product_data['product_url']}). Please visit our website to change subscription preferences
                                    """}}
                }
            )
        print(f"Email sent! Message ID: {response['MessageId']}")


if __name__ == "__main__":

    load_dotenv()

    conn = get_database_connection()
    ses_client = create_ses_client()

    current_datetime = datetime.now()

    headers = {
        'authority':  environ["AUTHORITY"],
        'user-agent': environ["USER_AGENT"]
    }
    
    products = get_all_product_data(conn)
    product_price_data = []

    for product in products:
        product_price = scrape_asos_page(conn, product, headers, ses_client)
        if product_price != 0:
            product_price_data.append((current_datetime, product["product_id"], product_price))

    insert_price_data(conn, product_price_data)



   





