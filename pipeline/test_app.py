"""
Unit tests for the file app.py.
"""

import pytest
import boto3
from unittest.mock import MagicMock, patch

from app import insert_user_data


@patch('app.boto3.client')
@patch('app.get_database_connection')
def test_insert_user_data(mock_get_database_connection, mock_boto3_client):
    """
    Tests that the it is only called once. 
    """
    mock_db_connection = MagicMock()
    mock_get_database_connection.return_value = mock_db_connection

    mock_ses_client = MagicMock()
    mock_boto3_client.return_value = mock_ses_client

    test_data = {'email': 'person1@email.com',
                 'first_name': 'John',
                 'last_name': 'Doe'}

    insert_user_data(mock_db_connection, test_data)
    mock_db_connection.insert.assert_called_once_with(test_data)
