"""
API.
"""
from os import environ

from dotenv import load_dotenv
from flask import Flask, render_template, request
from psycopg2 import connect, extras
from psycopg2.extensions import connection

from extract import scrape_asos_page

app = Flask(__name__, template_folder='./templates')


EMAIL_SELECTION_QUERY = "SELECT email FROM users;"
PRODUCT_URL_SELECTION_QUERY = "SELECT product_url FROM products;"


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
        query = "INSERT INTO users(email, first_name, last_name) VALUES (%s, %s, %s)"
        cur.execute(query, (data_user["email"],
                            data_user["first_name"],
                            data_user["last_name"]))

        conn.commit()
        cur.close()


def insert_product_data(conn: connection, data_product: dict):
    """
    Inserts product data into products table in the required database.
    """

    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute(PRODUCT_URL_SELECTION_QUERY)
    rows = cur.fetchall()

    product_urls = [row["product_url"] for row in rows]

    if data_product['product_url'] in product_urls:
        conn.commit()
        cur.close()

    else:

        query = "INSERT INTO products (product_name, product_url, website_name) VALUES (%s, %s, %s)"
        cur.execute(query, (data_product.get('product_name', 'Unknown'),
                            data_product['product_url'],
                            data_product['website_name']))
        conn.commit()
        cur.close()


def insert_subscription_data(conn: connection, user_email: str, product_url: str) -> None:
    """
    Inserts subscription data into the subscription table.
    """

    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    user_query = "SELECT user_id FROM users WHERE email = (%s);"

    cur.execute(user_query, (user_email,))

    user_id = cur.fetchone()['user_id']

    product_query = "SELECT product_id FROM products WHERE product_url = (%s);"

    cur.execute(product_query, (product_url,))

    product_id = cur.fetchone()['product_id']

    insert_query = "INSERT INTO subscriptions (user_id, product_id) VALUES (%s, %s);"

    cur.execute(insert_query, (user_id, product_id))

    conn.commit()


def get_products_from_email(conn: connection, email: str) -> list:
    """
    Returns list of products the user has subscribed to.
    """
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    query = """SELECT products.product_name
                FROM users JOIN subscriptions ON users.user_id = subscriptions.user_id
                JOIN products ON subscriptions.product_id = products.product_id WHERE users.email = (%s);"""
    cur.execute(query, (email,))

    return cur.fetchall()


@app.route("/")
def index():
    """
    Displays the HTML homepage.
    """
    return render_template('/index.html')


@app.route('/submit', methods=["POST", "GET"])
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
            'authority':  environ["AUTHORITY"],
            'user-agent': environ["USER_AGENT"]
        }

        product_data = scrape_asos_page(url, header)

        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email
        }

        insert_user_data(connection, user_data)
        insert_product_data(connection, product_data)
        insert_subscription_data(connection, email, url)

        return render_template('/submitted_form/submitted_form.html')

    if request.method == "GET":
        return render_template('/submission_form/input_website.html')


@app.route('/unsubscribe', methods=["GET", "POST"])
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

        user_products = get_products_from_email(conn, email)
        print(user_products)

        product_names = [product["product_name"]
                         for product in user_products]
        print(product_names)

        return render_template('unsubscribe/product_list.html', names=product_names)

    return render_template('/unsubscribe/unsubscribe_website.html')


@app.route("/submitted")
def submitted_form():
    """
    Displays the submitted form HTML page.
    """
    return render_template('/submitted_form/submitted_form.html')


if __name__ == "__main__":
    load_dotenv()
    app.run(debug=True)
