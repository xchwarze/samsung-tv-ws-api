"""Tests for the encrypted command."""

from __future__ import annotations

import json

from samsungtvws.encrypted.command import (
    SamsungTVEncryptedCommand,
    SamsungTVEncryptedPostCommand,
)

BODY = {"plugin": "RemoteControl", "param3": "KEY_POWER", "param4": False}


def test_command_payload() -> None:
    """Test a command serializes its method and body."""
    command = SamsungTVEncryptedCommand("GET", BODY)

    assert command.as_dict() == {"method": "GET", "body": BODY}
    assert json.loads(command.get_payload()) == {"method": "GET", "body": BODY}


def test_post_command() -> None:
    """Test the POST command sets the method."""
    command = SamsungTVEncryptedPostCommand(BODY)

    assert command.method == "POST"
    assert command.body == BODY
    assert command.as_dict() == {"method": "POST", "body": BODY}
