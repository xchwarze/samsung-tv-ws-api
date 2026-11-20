"""Tests for command module."""

import pytest

from samsungtvws.command import SamsungTVCommand, SamsungTVSleepCommand


def test_command_payload() -> None:
    """Ensure a command serializes its method and params."""
    command = SamsungTVCommand("ms.remote.control", {"Cmd": "Click"})
    assert command.as_dict() == {
        "method": "ms.remote.control",
        "params": {"Cmd": "Click"},
    }
    assert command.get_payload() == (
        '{"method": "ms.remote.control", "params": {"Cmd": "Click"}}'
    )


def test_sleep_command_delay() -> None:
    """Ensure a sleep command keeps its delay."""
    command = SamsungTVSleepCommand(2.5)
    assert command.method == "sleep"
    assert command.params == {}
    assert command.delay == 2.5


@pytest.mark.parametrize(
    "method",
    [
        pytest.param("as_dict", id="as-dict"),
        pytest.param("get_payload", id="get-payload"),
    ],
)
def test_sleep_command_not_serializable(method: str) -> None:
    """Ensure a sleep command cannot be serialized."""
    command = SamsungTVSleepCommand(1)
    with pytest.raises(NotImplementedError, match=f"Cannot use {method}"):
        getattr(command, method)()
