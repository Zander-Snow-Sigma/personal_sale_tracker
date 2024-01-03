
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


def get_product_data(rds_conn:connection):
    """Query database for data on all products that price data is required for"""

    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    # Get all unique products from product table
    cur.execute("SELECT product_id, product_url FROM products;")
    rows = cur.fetchall()
    cur.close()
  
    return rows


def scrape_asos_page(url: str, header: dict) -> dict:
    """
    Scrapes an ASOS page and returns a dict of desired data about the product.
    """
    page = requests.get(url, headers=header, timeout=5)
    soup = BeautifulSoup(page.text, "html.parser").find(
        "script", type="application/ld+json")
    try:
        product_data = json.loads(soup.string)

        product_price_data = {}
        
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
            product_price_data["price"] = price
        else:
            product_price_data["price"] = "Price not found"

        return product_price_data

    except AttributeError as error:
        return error



def insert_price_data(rds_conn: connection, product_data:dict):
    """Insert product_id, current product price and timestamp into prices table in database"""
    
    with rds_conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
        extras.execute_values(cur,
            """
            INSERT INTO prices (updated_at, product_id, price) 
            VALUES %s""",
            product_data)
        
    rds_conn.commit()
    

    

def send_email_for_invalid_url():
    """In instances where URL is inaccessible, drop product from table and send user email to notify of error"""
    pass


if __name__ == "__main__":

    load_dotenv()

    headers = {
        'authority':  environ["AUTHORITY"],
        'user-agent': environ["USER_AGENT"]
    }

    conn = get_database_connection()
    products = get_product_data(conn)
    

    # print(scrape_asos_page(environ['EXAMPLE_PAGE'], headers))
    current_datetime = datetime.now()
    product_price_data = []
    for product in products:
        product_price_data.append((current_datetime, product["product_id"], scrape_asos_page(product["product_url"], headers)["price"]))

    # print(product_price_data)
    insert_price_data(conn, product_price_data)
        


   





