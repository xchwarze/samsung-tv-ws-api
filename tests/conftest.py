"""Tests for remote module."""
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def override_time_sleep():
    """Open a websocket connection."""
    with patch("samsungtvws.remote.time.sleep"):
        yield


@pytest.fixture(name="connection")
def get_connection():
    """Open a websocket connection."""
    connection = Mock()
    with patch("samsungtvws.remote.websocket.create_connection") as connection_class:
        connection_class.return_value = connection
        yield connection
