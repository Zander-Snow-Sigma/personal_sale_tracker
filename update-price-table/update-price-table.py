"""
Script which scrapes webpages and inserts updated price data into prices table in RDS
Triggered every three minutes

To Do:
- Remove product from database when url becomes invalid
- Move verify email code to API script
"""

import json
from os import environ
from urllib.parse import urlparse
from psycopg2 import connect, extras
from psycopg2.extensions import connection

from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
import boto3

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


def get_all_product_data(rds_conn:connection):
    """
    Query database for data on all products that price data is required for
    """

    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    # Get all unique products from product table
    cur.execute("SELECT * FROM products;")
    rows = cur.fetchall()
    cur.close()
  
    return rows


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


def send_unsubscription_emails(rds_conn:connection, ses_client:boto3.client, product_data):
    """
    Set sender, recipient and condition for email
    """

    sender = 'trainee.harvind.grewal@sigmalabs.co.uk'
    recipients = get_user_emails(rds_conn, product_data['product_id'])

    ## Include email verification upon email entry on webpage ##
    for recipient in recipients:
        response = ses_client.verify_email_identity(
            EmailAddress=recipient
        )
    ## Include email verification upon email entry on webpage ##
        
    for recipient in recipients:
        response = ses_client.send_email(
            Source=sender,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': "Notification of product removed from tracking"},
                'Body': {'Text': {'Data': f"""
                                The product ({product_data['product_name']}) you have been tracking is no longer accessible by our system via the link provided 
                                ({product_data['product_url']}). Please visit our website to re-subscribe a product
                                """}}
            }
        )

    print(f"Email sent! Message ID: {response['MessageId']}")



def scrape_asos_page(rds_conn:connection, product: dict, header: dict, ses_client:boto3.client) -> dict:
    """
    Scrapes an ASOS page and returns a dict of desired data about the product.
    """
    page = requests.get(product["product_url"], headers=header, timeout=5)
    soup = BeautifulSoup(page.text, "html.parser").find(
        "script", type="application/ld+json")
    try:
        product_data = json.loads(soup.string)

        product_price = 0
        
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
            product_price = price
        else:
            product_price = "Price not found"

        return product_price

    except:
        # Remove product from table
        remove_invalid_product_from_database(rds_conn, product)
        # Send email to notify user
        send_unsubscription_emails(rds_conn, ses_client, product)
        

# def remove_invalid_product_from_database(rds_conn:connection, product:dict):
#     """
#     Remove product from product table when url is no longer accessible
#     """
#     curr = connection.cursor(cursor_factory=extras.RealDictCursor)
#     curr.execute(
#         "DELETE FROM product WHERE product_id = %s", (product['product_id'],))
#     connection.commit()
#     curr.close()
    


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
        
        product_price_data.append((current_datetime, product["product_id"], scrape_asos_page(conn, product, headers, ses_client)))
    
    print(product_price_data)

    insert_price_data(conn, product_price_data)

    
    # print(get_user_emails(conn,1))


   





