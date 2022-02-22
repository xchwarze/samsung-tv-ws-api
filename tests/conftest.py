"""Tests for remote module."""
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def override_time_sleep():
    """Ignore time sleep in tests."""
    with patch("samsungtvws.connection.time.sleep"), patch(
        "samsungtvws.remote.time.sleep"
    ):
        yield


@pytest.fixture(name="connection")
def get_connection():
    """Open a websocket connection."""
    connection = Mock()
    with patch(
        "samsungtvws.connection.websocket.create_connection"
    ) as connection_class:
        connection_class.return_value = connection
        yield connection
