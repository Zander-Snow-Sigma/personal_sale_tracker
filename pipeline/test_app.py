"""
Unit tests for the file app.py.
"""
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

from app import insert_user_data, insert_product_data, insert_subscription_data, get_products_from_email


def test_insert_user_data_no_insert():
    """
    Tests that execute is only called once when
    the email is already in the database. 
    """

    test_data = {'email': 'person1@email.com',
                 'first_name': 'John',
                 'last_name': 'Doe'}

    emails = [{"email": 'person1@email.com'}]

    mock_db_connection = MagicMock()
    mock_execute = mock_db_connection.cursor().execute
    mock_fetchall = mock_db_connection.cursor().fetchall

    mock_fetchall.return_value = emails

    insert_user_data(mock_db_connection, test_data)

    mock_execute.assert_called_once()


@patch("app.get_ses_client")
def test_insert_user_data_correct(mock_get_ses_client):
    """
    Tests that execute is called twice and verify email is called once
    when the email is not in the database.
    """

    test_data = {'email': 'person1@email.com',
                 'first_name': 'John',
                 'last_name': 'Doe'}

    emails = [{"email": 'person2@email.com'}]

    mock_db_connection = MagicMock()
    mock_execute = mock_db_connection.cursor().execute
    mock_fetchall = mock_db_connection.cursor().fetchall

    mock_fetchall.return_value = emails

    mock_ses = MagicMock()

    mock_get_ses_client.return_value = mock_ses

    mock_verify_email = mock_ses.verify_email_address

    insert_user_data(mock_db_connection, test_data)

    assert mock_verify_email.call_count == 1
    assert mock_execute.call_count == 2


def test_insert_product_data_no_insert():
    """
    Tests that execute is called once if the product
    is already in the database.
    """

    test_data = {"product_name": "test product"}

    product_data = [{"product_name": "test product"}]

    mock_db_connection = MagicMock()
    mock_execute = mock_db_connection.cursor().execute
    mock_fetchall = mock_db_connection.cursor().fetchall

    mock_fetchall.return_value = product_data

    insert_product_data(mock_db_connection, test_data)

    assert mock_execute.call_count == 1


def test_insert_product_data_correct():
    """
    Tests that execute is called twice when the product is not in the database.
    """

    test_data = {"product_name": "test product", "product_url": "test_url",
                 "image_URL": "test_url", "is_in_stock": True, "website_name": "asos"}

    product_data = [{"product_name": "product1", "product_url": "test_url",
                     "image_URL": "test_url", "is_in_stock": True, "website_name": "asos"}]

    mock_db_connection = MagicMock()
    mock_execute = mock_db_connection.cursor().execute
    mock_fetchall = mock_db_connection.cursor().fetchall

    mock_fetchall.return_value = product_data

    insert_product_data(mock_db_connection, test_data)

    assert mock_execute.call_count == 2


def test_insert_subscription_data_no_insert():
    """
    Tests that execute is called three times when the subscription is in the database.
    """

    test_email = "test@email.com"
    test_url = "test_url"

    mock_data = {"user_id": 2, "product_id": 5}

    mock_db_connection = MagicMock()
    mock_execute = mock_db_connection.cursor().execute
    mock_fetchone = mock_db_connection.cursor().fetchone

    mock_fetchone.return_value = mock_data

    insert_subscription_data(mock_db_connection, test_email, test_url)

    assert mock_execute.call_count == 3


def test_get_products_from_email():
    """
    Tests execute is called once.
    """

    mock_conn = MagicMock()
    email = "example@email.com"

    mock_execute = mock_conn.cursor().execute

    get_products_from_email(mock_conn, email)

    assert mock_execute.call_count == 1


@patch("app.insert_subscription_data")
@patch("app.insert_product_data")
@patch("app.insert_user_data")
@patch("app.scrape_asos_page")
@patch("app.get_database_connection")
@patch("app.render_template")
def test_submit_post(mock_render_template, mock_get_database_connection,
                     mock_scrape_asos_page, mock_insert_user_data,
                     mock_insert_product_data, mock_insert_subscription_data, api_client):
    """
    Tests a post request to the addproducts returns a 200 status code.
    """

    load_dotenv()

    response = api_client.post("/addproducts", data={
        "firstName": "zander",
        "lastName": "snow",
        "email": "test@email.com",
        "url": "test.com"
    })

    assert response.status_code == 200


@patch("app.insert_subscription_data")
@patch("app.insert_product_data")
@patch("app.insert_user_data")
@patch("app.scrape_asos_page")
@patch("app.get_database_connection")
@patch("app.render_template")
def test_submit_get(mock_render_template, mock_get_database_connection,
                    mock_scrape_asos_page, mock_insert_user_data,
                    mock_insert_product_data, mock_insert_subscription_data, api_client):
    """
    Tests a get request to the addproducts returns a 200 status code.
    """

    load_dotenv()

    response = api_client.get("/addproducts")

    assert response.status_code == 200


@patch("app.insert_subscription_data")
@patch("app.insert_product_data")
@patch("app.insert_user_data")
@patch("app.scrape_asos_page")
@patch("app.get_database_connection")
@patch("app.render_template")
def test_subscriptions_post(mock_render_template, mock_get_database_connection,
                            mock_scrape_asos_page, mock_insert_user_data,
                            mock_insert_product_data, mock_insert_subscription_data, api_client):
    """
    Tests a post request to the subscriptions page returns a 200 status code.
    """

    load_dotenv()

    response = api_client.post("/subscriptions", data={
        "email": "test@email.com"
    })

    assert response.status_code == 200


@patch("app.get_database_connection")
def test_delete_subscriptions_post(mock_get_database_connection, api_client):
    """
    Tests a post request to the delete subscriptions page returns a 200 status code.
    """

    load_dotenv()

    response = api_client.post("/delete_subscription", data={
        "email": "test@email.com"
    })

    assert response.status_code == 200


@patch("app.get_database_connection")
def test_submitted_post(mock_get_database_connection, api_client):
    """
    Tests a post request to the submitted page returns a 200 status code.
    """

    load_dotenv()

    response = api_client.post("/submitted", data={
        "email": "test@email.com"
    })

    assert response.status_code == 200
