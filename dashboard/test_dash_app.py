"""
Script to test the dashboard app. 
"""
import bcrypt
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from app import authenticate_user, handle_login, logout_of_dashboard
from database import get_database_connection, load_all_database_info, get_user_info


@pytest.fixture
def users():
    """
    Fixture for example users to be tested.
    """
    return [
        {'email': 'person1@email.com',
            'password': bcrypt.hashpw('password1'.encode('utf-8'), bcrypt.gensalt())},
        {'email': 'person2@email.com',
            'password': bcrypt.hashpw('password2'.encode('utf-8'), bcrypt.gensalt())}
    ]


def test_authenticate_correct_password(users):
    """
    Tests that the function successfully validates a correct password.
    """
    user = authenticate_user(users, 'person1@email.com', 'password1')
    assert user is not None


def test_reject_incorrect_password(users):
    """
    Tests that incorrect passwords are not authenticated.
    """

    user = authenticate_user(users, 'person1@email.com', 'hello1')
    assert user is None


def test_reject_unknown_user(users):
    """
    Tests that unknown users are not authenticated.
    """

    user = authenticate_user(users, 'unknown_person@email.com', 'password1')
    assert user is None


@patch('app.authenticate_user')
@patch('app.st.session_state')
@patch('app.st.error')
def test_handle_login(mock_st_error, mock_session_state, mock_authenticate_user):
    """
    Tests that an error is not called, and that logged_in, user_email
    and user_id are each called once when the login is successful. 
    """
    mock_authenticate_user.return_value = {
        'user_id': 1, 'email': 'person@email.com'}
    handle_login(
        users=mock_authenticate_user.return_value,
        email='person@email.com',
        password='password1',
        cookie_manager=MagicMock()
    )

    assert mock_session_state.__setitem__.call_count == 3
    mock_st_error.assert_not_called()


@patch('app.st.session_state')
def test_handle_logout(mock_session_state):
    """
    Tests that that logged_in, user_email and user_id are each 
    called once when the user is logged out. 
    """
    cookie_manager = MagicMock()
    logout_of_dashboard(cookie_manager)

    assert mock_session_state.__setitem__.call_count == 3


@patch.dict("os.environ", {
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_password",
    "DB_HOST": "test_host",
    "DB_PORT": "1234",
    "DB_NAME": "test_db"})
@patch("database.connect")
def test_get_database_connection_successful(mock_connect):
    """
    Testing connection to database.
    """
    expected_connection = MagicMock()
    mock_connect.return_value = expected_connection
    result = get_database_connection()

    assert result == expected_connection


@patch.dict("os.environ", {
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_password",
    "DB_HOST": "test_host",
    "DB_PORT": "1234",
    "DB_NAME": "test_db"})
@patch("database.connect", side_effect=ConnectionError("Connection error"))
def test_get_database_connection_connection_error(mock_connect):
    """
    Testing failed connection to database.
    """
    result = get_database_connection()

    assert isinstance(result, ConnectionError)


@patch("database.connect")
def test_load_all_database_info(mock_connect):
    """
    Test that checks data is returned in the format of COLUMNS as specified in the SELECT_ALL_QUERY.
    """
    mock_connection = MagicMock()
    mock_cursor = mock_connection.cursor.return_value.__enter__.return_value
    mock_cursor.fetchall.return_value = [
        {"price_id": 1, "updated_at": "2022-01-01", "price": 100.0, "product_id": 123,
         "product_name": "Example Product", "product_url": "http://example.com",
         "image_url": "http://example.com/image.jpg", "product_availability": "In Stock",
         "website_name": "Example Website", "user_id": 456, "first_name": "John",
         "last_name": "Doe", "email": "john.doe@example.com", "subscription_id": 789}
    ]
    result = load_all_database_info(mock_connection)

    # Check that result is in the form of a data frame
    assert isinstance(result, pd.DataFrame)

    expected_df = pd.DataFrame([
        {"Price ID": 1, "Updated At": "2022-01-01", "Price": 100.0, "Product ID": 123,
         "Product Name": "Example Product", "Product URL": "http://example.com",
         "Image URL": "http://example.com/image.jpg", "Product Availability": "In Stock",
         "Website Name": "Example Website", "User ID": 456, "User FirstName": "John",
         "User LastName": "Doe", "User Email": "john.doe@example.com", "Subscription ID": 789}
    ])
    # Check if column names are appropriately renamed
    assert result.equals(expected_df)


@patch("database.connection")
@patch("database.hash_password")
def test_get_user_info(mock_hash_password, mock_connection):
    """
    Test that all user information is retrieved from database and admin login details are created.
    """
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value

    mock_cursor.fetchall.return_value = [
        {"user_id": 1, "email": "user1@example.com",
            "first_name": "John", "last_name": "Doe"},
        {"user_id": 2, "email": "user2@example.com",
            "first_name": "Jane", "last_name": "Smith"}
    ]

    mock_hash_password.side_effect = lambda password: f"hashed_{password}"

    result = get_user_info(mock_conn)

    assert isinstance(result, list)
    assert len(result) == 3

    # Admin user
    assert result[0] == {
        "user_id": 0,
        "email": "admin@saletracker.co.uk",
        "type": "admin",
        "first_name": "Admin",
        "last_name": "Admin",
        "password": "hashed_adminPassword"
    }

    # Regular users
    assert result[1] == {
        "user_id": 1,
        "email": "user1@example.com",
        "type": "user",
        "first_name": "John",
        "last_name": "Doe",
        "password": "hashed_userPassword"
    }

    assert result[2] == {
        "user_id": 2,
        "email": "user2@example.com",
        "type": "user",
        "first_name": "Jane",
        "last_name": "Smith",
        "password": "hashed_userPassword"
    }
