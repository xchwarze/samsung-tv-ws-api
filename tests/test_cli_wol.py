"""Tests for cli wol module."""

from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from samsungtvws.cli import cli

BASE_ARGS = ["--host", "127.0.0.1", "--no-print-token"]
MAC = "aa:bb:cc:dd:ee:ff"


@pytest.fixture(name="send_magic_packet")
def get_send_magic_packet() -> Iterator[Mock]:
    """Patch the Wake-on-LAN packet sender."""
    with patch("wakeonlan.send_magic_packet") as send:
        yield send


@pytest.mark.parametrize(
    ("extra_args", "port"),
    [
        pytest.param([], 9, id="default-port"),
        pytest.param(["--wol-port", "7"], 7, id="custom-port"),
    ],
)
def test_wol(send_magic_packet: Mock, extra_args: list[str], port: int) -> None:
    """Ensure the magic packet is sent to the MAC address."""
    result = CliRunner().invoke(cli, [*BASE_ARGS, "wol", MAC, *extra_args])
    assert result.exit_code == 0
    assert result.stdout == f"OK: magic packet sent to {MAC}\n"
    send_magic_packet.assert_called_once_with(MAC, port=port)
