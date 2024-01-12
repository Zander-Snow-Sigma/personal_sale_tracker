"""
API.
"""
from os import environ, _Environ
from datetime import datetime

from boto3 import client
from mypy_boto3_ses import SESClient
from dotenv import load_dotenv
from flask import Flask, render_template, request
from psycopg2 import connect, extras
from psycopg2.extensions import connection

from extract import scrape_asos_page

app = Flask(__name__, template_folder='./templates')


EMAIL_SELECTION_QUERY = "SELECT email FROM users;"
PRODUCT_URL_SELECTION_QUERY = "SELECT product_name FROM products;"
INSERT_USER_DATA_QUERY = "INSERT INTO users(email, first_name, last_name) VALUES (%s, %s, %s)"
INSERT_INTO_PRODUCTS_QUERY = """
                INSERT INTO products (product_name, product_url, image_url, product_availability, website_name) 
                VALUES (%s, %s, %s, %s, %s)
                """
PRODUCT_ID_QUERY = "SELECT product_id FROM products WHERE product_url = (%s)"
INSERT_INTO_PRICES_QUERY = "INSERT INTO prices (updated_at, product_id, price) VALUES (%s, %s, %s)"
SELECT_SUB_BY_PRODUCT_AND_USER_QUERY = "SELECT * FROM subscriptions WHERE user_id = (%s) AND product_id = (%s);"
INSERT_INTO_SUBSCRIPTIONS_QUERY = "INSERT INTO subscriptions (user_id, product_id) VALUES (%s, %s);"
SELECT_USERS_BY_EMAIL_QUERY = "SELECT user_id FROM users WHERE email = (%s);"
GET_PRODUCTS_FROM_EMAIL_QUERY = """
                SELECT users.first_name, products.product_name,products.product_url, products.product_id, products.image_url, products.product_availability
                FROM users
                JOIN subscriptions ON users.user_id = subscriptions.user_id
                JOIN products ON subscriptions.product_id = products.product_id
                WHERE users.email = (%s);  
                """
GET_SUBS_BY_EMAIL_QUERY = """
                SELECT subscriptions.user_id
                FROM subscriptions
                JOIN users ON subscriptions.user_id = users.user_id
                WHERE users.email = (%s);
                """
GET_PROD_ID_BY_PROD_NAME_QUERY = "SELECT product_id FROM products WHERE product_name = %s;"
DELETE_SUBSCRIPTIONS_QUERY = "DELETE FROM subscriptions WHERE product_id = (%s) AND user_id = (%s);"


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


def insert_user_data(conn: connection, data_user: dict):
    """
    Inserts user data into users table in required database.
    """
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute(EMAIL_SELECTION_QUERY)
    rows = cur.fetchall()

    emails = [row["email"] for row in rows]

    if data_user['email'] in emails:
        conn.commit()
        cur.close()

    else:
        query = INSERT_USER_DATA_QUERY
        cur.execute(query, (data_user["email"],
                            data_user["first_name"],
                            data_user["last_name"]))

        conn.commit()
        cur.close()

        ses_client = get_ses_client(environ)

        ses_client.verify_email_address(
            EmailAddress=data_user['email'])


def insert_product_data_and_price_data(conn: connection, data_product: dict):
    """
    Inserts product data into products table in the required database.
    Also inserts price data into the prices table if product has just been
    added for the first time.
    """

    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute(PRODUCT_URL_SELECTION_QUERY)
    rows = cur.fetchall()
    current_timestamp = datetime.now()

    product_urls = [row["product_name"] for row in rows]

    if data_product['product_name'] in product_urls:
        conn.commit()
        cur.close()

    else:

        query = INSERT_INTO_PRODUCTS_QUERY
        cur.execute(query, (data_product.get('product_name', 'Unknown'),
                            data_product['product_url'],
                            data_product['image_URL'],
                            data_product['is_in_stock'],
                            data_product['website_name']))

        product_id_query = PRODUCT_ID_QUERY

        cur.execute(product_id_query, (data_product["product_url"],))

        product_id = cur.fetchone()

        price_query = INSERT_INTO_PRICES_QUERY
        cur.execute(price_query, (current_timestamp,
                                  product_id["product_id"],
                                  data_product["price"]))
        conn.commit()
        cur.close()


def insert_subscription_data(conn: connection, user_email: str, product_url: str) -> None:
    """
    Inserts subscription data into the subscription table.
    """

    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    user_query = SELECT_USERS_BY_EMAIL_QUERY
    cur.execute(user_query, (user_email,))
    user_id = cur.fetchone().get('user_id')

    product_query = PRODUCT_ID_QUERY
    cur.execute(product_query, (product_url,))
    product_id = cur.fetchone().get('product_id')

    check_query = SELECT_SUB_BY_PRODUCT_AND_USER_QUERY
    cur.execute(check_query, (user_id, product_id))

    if cur.fetchone() is None:
        insert_query = INSERT_INTO_SUBSCRIPTIONS_QUERY

        cur.execute(insert_query, (user_id, product_id))

        conn.commit()


def get_products_from_email(conn: connection, email: str) -> list:
    """
    Returns list of products the user has subscribed to.
    """
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute(GET_PRODUCTS_FROM_EMAIL_QUERY, (email,))

    return cur.fetchall()


def get_ses_client(config: _Environ) -> SESClient:
    """
    Returns an SES client to send emails to users.
    """

    return client('ses',
                  aws_access_key_id=config['AWS_ACCESS_KEY'],
                  aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY'])


@app.route("/")
def index():
    """
    Displays the HTML homepage.
    """
    return render_template('/index.html')


@app.route('/addproducts', methods=["POST", "GET"])
def submit():
    """
    Handles data submissions.
    """
    connection = get_database_connection()
    if request.method == 'POST':
        first_name = request.form.get('firstName').capitalize()
        last_name = request.form.get('lastName').capitalize()
        email = request.form.get('email')
        url = request.form.get('url')

        header = {
            'user-agent': environ["USER_AGENT"]
        }

        product_data = scrape_asos_page(url, header)

        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email
        }

        insert_user_data(connection, user_data)
        insert_product_data_and_price_data(connection, product_data)
        insert_subscription_data(connection, email, url)

        return render_template('/submitted_form/submitted_form.html')

    if request.method == "GET":
        return render_template('/submission_form/input_website.html')


@app.route('/subscriptions', methods=["GET", "POST"])
def unsubscribe_index():
    """
    Displays the unsubscribe HTML page.
    """
    conn = get_database_connection()
    if request.method == "POST":
        email = request.form.get('email')

        cur = conn.cursor(cursor_factory=extras.RealDictCursor)

        cur.execute(EMAIL_SELECTION_QUERY)
        rows = cur.fetchall()

        emails = [row["email"] for row in rows]

        if email not in emails:
            return render_template('/unsubscribe/not_subscribed.html')

        query = GET_SUBS_BY_EMAIL_QUERY

        cur.execute(query, (email,))

        result = cur.fetchall()

        if not result:
            return render_template('/unsubscribe/not_subscribed.html')

        user_products = get_products_from_email(conn, email)

        for user in user_products:
            if user["product_availability"] == True:
                user["available"] = "In Stock"
            else:
                user["available"] = "Out of Stock"

        user_first_name = [product["first_name"]
                           for product in user_products][0]

        num_of_products = len(user_products)

        return render_template('unsubscribe/product_list.html',
                               names=user_products,
                               firstname=user_first_name,
                               user_email=email,
                               num_products=num_of_products)

    return render_template('/unsubscribe/unsubscribe_website.html')


@app.route('/delete_subscription', methods=["POST"])
def delete_subscription():
    """
    Deletes subscriptions.
    """
    conn = get_database_connection()
    product_name = request.form.get("product_name")
    email = request.form.get('user_email')

    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute(GET_PROD_ID_BY_PROD_NAME_QUERY, (product_name,))
    product_id = cur.fetchone()['product_id']

    cur.execute(SELECT_USERS_BY_EMAIL_QUERY, (email,))
    user_id = cur.fetchone()['user_id']

    cur.execute(DELETE_SUBSCRIPTIONS_QUERY,
                (product_id, user_id))
    conn.commit()

    return 'Subscription deleted successfully', 200


@app.route("/submitted", methods=["POST"])
def submitted_form():
    """
    Displays the submitted form HTML page.
    """

    return render_template('/submitted_form/submitted_form.html')


if __name__ == "__main__":
    load_dotenv()
    app.run(debug=True, host="0.0.0.0")
