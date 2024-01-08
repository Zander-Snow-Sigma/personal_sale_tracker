"""
Script to test the dashboard app. 
"""
import pytest
import bcrypt
from unittest.mock import patch, MagicMock
from app import authenticate_user, handle_login, logout_of_dashboard


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
