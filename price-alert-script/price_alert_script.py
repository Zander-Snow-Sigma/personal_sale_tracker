"""
Script which compares latest product prices with prior entires 
and notifies user if price drops.
"""
import logging
from os import environ
from datetime import datetime

from dotenv import load_dotenv
import boto3
from psycopg2 import connect, extras
from psycopg2.extensions import connection

logging.basicConfig(filename='price_alert_logs.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


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


def get_prices_of_latest_pair_of_products(
        rds_conn: connection, product_id_of_interest: int) -> list:
    """
    Query RDS prices table for product prices. 
    Returns a list of of dictionaries of the two most recent products in 
    the prices table with the specified ID.
    """
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT * FROM prices WHERE product_id = (%s) ORDER BY updated_at DESC LIMIT 2;",
                (product_id_of_interest,))
    latest_prices = cur.fetchall()
    cur.close()

    latest_prices = [dict(row) for row in latest_prices]
    for row in latest_prices:
        row['updated_at'] = datetime.fromtimestamp(
            row['updated_at'].timestamp()).strftime('%Y-%m-%d %H:%M:%S.%f')
        row['price'] = float(row['price'])

    latest_prices = sorted(latest_prices, key=lambda x: x['product_id'])

    return latest_prices


def compare_latest_two_prices(latest_price_entries: dict) -> bool:
    """
    Compare values of price for last two  entries of each product for that specific ID.
    """

    try:
        if len(latest_price_entries) > 1:
            return latest_price_entries[-2]['price'] < latest_price_entries[-1]['price']

    except UnboundLocalError:
        return False


def get_discount_amount(latest_prices_list: list) -> dict:
    """
    Gets the old and new product price. 
    Calculates the percentage discount. 
    """
    if len(latest_prices_list) > 1 and latest_prices_list[-1].get(
            'price') and latest_prices_list[0].get('price'):

        previous_price = latest_prices_list[-1].get('price')
        new_price = latest_prices_list[0].get('price')

        discount_value = previous_price - new_price
        fractional_discount = discount_value/previous_price
        percentage_discount = fractional_discount * 100

        return {'previous_price': previous_price,
                'new_price': new_price,
                'percentage_discount': percentage_discount}

    return {'previous_price': 'Could not extract.',
            'new_price': 'Could not extract.',
            'percentage_discount': 'Unknown'}


def get_user_emails(rds_conn: connection) -> list[dict]:
    """
    Query RDS for every instance of a subscription.
    Collects all the relevant information to check if there is a discount:
    user ID, user email, product id, product name, discount status.
    """
    list_of_subscription_instances = []
    cur = rds_conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT * FROM subscriptions;")
    all_subscriptions = [dict(row) for row in cur.fetchall()]

    for subscription in all_subscriptions:

        user_id = subscription['user_id']
        product_id = subscription['product_id']

        cur.execute("SELECT email FROM users WHERE user_id = (%s);", (user_id,))
        user_email = [dict(row) for row in cur.fetchall()][0]['email']

        cur.execute(
            "SELECT product_name, image_url FROM products WHERE product_id = (%s);", (product_id,))
        response = [dict(row) for row in cur.fetchall()][0]
        product_name = response['product_name']
        image_url = response['image_url']

        latest_products = get_prices_of_latest_pair_of_products(
            rds_conn, product_id)
        is_discounted = compare_latest_two_prices(latest_products)
        prices_and_discount_amount = get_discount_amount(latest_products)

        previous_price = prices_and_discount_amount['previous_price']
        new_price = prices_and_discount_amount['new_price']
        percentage_discount = prices_and_discount_amount['percentage_discount']

        cur.execute(
            "SELECT product_url FROM products WHERE product_id = (%s);", (product_id,))
        product_url = [dict(row) for row in cur.fetchall()][0]['product_url']

        list_of_subscription_instances.append({
            'user_id': user_id,
            'user_email': user_email,
            'product_id': product_id,
            'product_name': product_name,
            'is_discounted': is_discounted,
            'previous_price': previous_price,
            'new_price': new_price,
            'percentage_discount': percentage_discount,
            'image_url': image_url,
            'product_url': product_url
        })

    return list_of_subscription_instances


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
    """
    Sends an email with desired subject and body.
    """

    response = ses_client.send_email(
        Source=sender,
        Destination={'ToAddresses': [recipient]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Html': {'Data': body}}
        }
    )

    logging.info(f"Email sent! Message ID: {response['MessageId']}")


def selectively_send_emails(ses_client, subscription_instances: list[list]):
    """
    Selectively sending emails to users if price drops
    """

    sender = 'trainee.tayla.dawson@sigmalabs.co.uk'

    for subscription in subscription_instances:
        if subscription['is_discounted'] == True:
            recipient = subscription['user_email']
            subject = "Your item has decreased in price!"

            body = f"""<meta charset="UTF-8">
                            <center>
                            <h1 font-family="Ariel">
                            Your item <a href={subscription['product_url']}>
                            {subscription['product_name']}</a> has gone down 
                            by {subscription['percentage_discount']:.1f}%
                            </h1>
                            <body class="New price" font-family="Ariel">
                            <b>
                            New price = £{subscription['new_price']:.2f}
                            </body><br></br>
                            <body class="Previous price" font-family="Ariel">
                            <b>Previous price = £{subscription['previous_price']:.2f}
                            </b>
                            </body><br></br>
                            <img src="{subscription["image_url"]}" alt="img">
                            </center>"""

            send_email(ses_client, sender, recipient, subject, body)

        else:
            logging.info("Email not sent; no price change.")


if __name__ == "__main__":

    load_dotenv()
    conn = get_database_connection()

    user_product_booleans = get_user_emails(conn)
    client = create_ses_client()
    selectively_send_emails(client, user_product_booleans)
