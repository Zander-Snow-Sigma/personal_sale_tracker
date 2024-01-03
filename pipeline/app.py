"""
API.
"""
from os import environ

from dotenv import load_dotenv
from flask import Flask, render_template, request
from psycopg2 import connect, extras
from psycopg2.extensions import connection

from extract import scrape_asos_page

app = Flask(__name__, template_folder='../templates')


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


@app.route('/')
def index():
    """
    Displays the HTML homepage.
    """
    return render_template('input_website.html')


@app.route('/submit', methods=["POST"])
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

    return render_template('input_website.html')


if __name__ == "__main__":
    load_dotenv()
    app.run(debug=True)
