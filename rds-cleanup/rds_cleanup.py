"""
Script which transfers price data from an RDS to a CSV file in an S3 bucket.
"""

# 1. Get all but last couple data from RDS
# 2. Combine to single table in pandas
# 3. Save to CSV in S3 bucket
# 4. Remove all but last couple price data from RDS

from io import StringIO
from os import _Environ, environ

from boto3 import client
from dotenv import load_dotenv
from mypy_boto3_s3 import S3Client
import pandas as pd
from psycopg2 import connect
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor


SELECT_QUERY = """SELECT prices.price_id, prices.updated_at, prices.price, products.product_id, products.product_name, products.product_url, products.website_name, products.image_url, products.product_availability, users.user_id, users.email, users.first_name, users.last_name, subscriptions.subscription_id
                FROM prices
                JOIN products ON products.product_id = prices.product_id
                JOIN subscriptions ON subscriptions.product_id = products.product_id
                JOIN users ON users.user_id = subscriptions.user_id
                WHERE prices.price_id NOT IN (
                SELECT DISTINCT ON (product_id) price_id
                FROM prices ORDER BY product_id, updated_at DESC
                );"""

DELETE_QUERY = """DELETE FROM prices
                WHERE price_id IN (
                    SELECT price_id FROM prices
                    WHERE price_id NOT IN (
                        SELECT DISTINCT ON (product_id) price_id FROM prices
                        ORDER BY product_id, updated_at DESC
                        )
                        );"""

COLUMNS = {"price_id": "Price ID", "updated_at": "Updated At", "price": "Price", "product_id": "Product ID", "product_name": "Product Name", "product_url": "Product URL", "image_url": "Image URL",
           "product_availability": "Product Availability", "website_name": "Website Name", "user_id": "User ID", "first_name": "User FirstName", "last_name": "User LastName", "email": "User Email", "subscription_id": "Subscription ID"}


def get_db_connection(config: _Environ) -> connection:
    """
    Returns a connection to a database with the given configuration.
    """

    return connect(
        user=config["DB_USER"],
        password=config["DB_PASSWORD"],
        host=config["DB_HOST"],
        port=config["DB_PORT"],
        database=config["DB_NAME"]
    )


def get_s3_client(config: _Environ) -> S3Client:
    """Get a connection to the relevant S3 bucket."""
    s3_client = client("s3",
                       aws_access_key_id=config["AWS_ACCESS_KEY_ID"],
                       aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY"])
    return s3_client


def extract_old_data_from_database(db_conn: connection) -> pd.DataFrame:
    """Extract all data from the database."""

    with db_conn.cursor(cursor_factory=RealDictCursor) as cur:

        cur.execute(SELECT_QUERY)

        result = cur.fetchall()

        return pd.DataFrame(result).rename(columns=COLUMNS)


def get_archive_data_csv(s3_client: S3Client, bucket: str, key: str) -> pd.DataFrame:
    """Retrieves the archived data from an S3 bucket."""

    obj = s3_client.get_object(Bucket=bucket, Key=key)
    csv_str = obj["Body"].read().decode()
    return pd.read_csv(StringIO(csv_str))


def update_archive_data(arch_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """Updates the archived dataframe with new data."""

    return pd.concat([arch_df, new_df], axis=0)


if __name__ == "__main__":

    load_dotenv()

    conn = get_db_connection(environ)

    s3 = get_s3_client(environ)

    old_data = extract_old_data_from_database(conn)

    local_arch_data = pd.read_csv("archived_data.csv")

    archived_data = get_archive_data_csv(
        s3, "c9-sale-tracker-bucket", "archived_data.csv")

    # BUG here - values missing for many columns??
    updated_data = update_archive_data(local_arch_data, old_data)
