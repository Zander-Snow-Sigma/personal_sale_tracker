"""
Tests the update price and send alerts script.
"""
import pytest
import unittest
from unittest.mock import patch, MagicMock

from update_price_and_send_alerts import get_database_connection, get_all_product_data, get_user_data, get_discount_amount, send_price_update_email


@patch.dict("os.environ", {
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_password",
    "DB_HOST": "test_host",
    "DB_PORT": "1234",
    "DB_NAME": "test_db"})
@patch("update_price_and_send_alerts.connect")
def test_get_database_connection_successful(mock_rds_conn):
    """
    Testing connection to database.
    """
    expected_connection = MagicMock()
    mock_rds_conn.return_value = expected_connection
    result = get_database_connection()

    assert result == expected_connection


@patch.dict("os.environ", {
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_password",
    "DB_HOST": "test_host",
    "DB_PORT": "1234",
    "DB_NAME": "test_db"})
@patch("update_price_and_send_alerts.connect", side_effect=ConnectionError("Connection error"))
def test_get_database_connection_connection_error(mock_rds_conn):
    """
    Testing failed connection to database.
    """
    result = get_database_connection()

    assert isinstance(result, ConnectionError)


@patch("update_price_and_send_alerts.connect")
def test_get_all_product_data(mock_rds_conn):
    """
    Testing that function is able to retrieve all product information from database.
    """
    mock_cursor = MagicMock()
    mock_fetchall = MagicMock(
        return_value=[{'id': 1, 'name': 'Product1'}, {'id': 2, 'name': 'Product2'}])
    mock_cursor.fetchall = mock_fetchall

    mock_rds_conn.cursor.return_value = mock_cursor

    # Call the function under test
    result = get_all_product_data(mock_rds_conn)

    expected_result = [{'id': 1, 'name': 'Product1'},
                       {'id': 2, 'name': 'Product2'}]
    assert result == expected_result


@patch("update_price_and_send_alerts.connect")
def test_get_user_data(mock_rds_conn):
    """
    Testing that function is able to retrieve user email from database.
    """
    mock_cursor = MagicMock()
    mock_fetchall = MagicMock(
        return_value=[{'email': 'user1@example.com'}, {'email': 'user2@example.com'}])
    mock_cursor.fetchall = mock_fetchall
    mock_rds_conn.cursor.return_value = mock_cursor

    product_id = 1
    result = get_user_data(mock_rds_conn, product_id)

    expected_result = ['user1@example.com', 'user2@example.com']
    assert result == expected_result


def test_get_discount_amount():
    """
    Test that it is possible to calculate a products discount based on new and old price.
    """

    assert get_discount_amount(10.0, 5.0) == {'previous_price': 10.0,
                                              'new_price': 5.0,
                                              'percentage_discount': 50.0}


def test_get_discount_amount_invalid_input():
    """
    Test that a products discount for invalid price input returns an error.
    """

    assert get_discount_amount('', '') == {'previous_price': 'Could not extract.',
                                           'new_price': 'Could not extract.',
                                           'percentage_discount': 'Unknown'}


@pytest.fixture
def mock_ses_client():
    with patch("update_price_and_send_alerts.boto3.client") as mock_ses:
        yield mock_ses


@patch("update_price_and_send_alerts.get_discount_amount")
def test_send_price_update_email(mock_get_discount_amount, mock_ses_client):
    """
    Test that the calculate discount function is called once and that an 
    email is sent to every user subscribed to a given product.
    """

    mock_get_discount_amount.return_value = {
        "percentage_discount": 10.0,
        "new_price": 90.0,
        "previous_price": 100.0,
    }

    mock_ses = MagicMock()
    mock_ses_client.return_value = MagicMock()

    product_data = {
        "product_name": "Product123",
        "product_url": "https://example.com/product/123",
        "image_url": "https://example.com/image/123.jpg",
    }

    recipients = ["user1@example.com", "user2@example.com"]
    old_price = 100.0
    new_price = 90.0
    send_price_update_email(mock_ses, product_data,
                            recipients, old_price, new_price)

    mock_get_discount_amount.assert_called_once_with(old_price, new_price)

    assert mock_ses.send_email.call_count == 2
