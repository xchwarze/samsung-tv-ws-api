"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2025 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import typer

from samsungtvws import SamsungTVShortcuts

from .main import cli, get_tv


def _sc(ctx: typer.Context) -> SamsungTVShortcuts:
    return get_tv(ctx).shortcuts()


@cli.command("power")
def power(ctx: typer.Context) -> None:
    """
    Toggle TV power (KEY_POWER).
    """
    _sc(ctx).power()


@cli.command("home")
def home(ctx: typer.Context) -> None:
    """
    Open Home screen (KEY_HOME).
    """
    _sc(ctx).home()


@cli.command("menu")
def menu(ctx: typer.Context) -> None:
    """
    Open Menu (KEY_MENU).
    """
    _sc(ctx).menu()


@cli.command("source")
def source(ctx: typer.Context) -> None:
    """
    Open Source selection (KEY_SOURCE).
    """
    _sc(ctx).source()


@cli.command("back")
def back(ctx: typer.Context) -> None:
    """
    Go back / return (KEY_RETURN).
    """
    _sc(ctx).back()


@cli.command("up")
def up(ctx: typer.Context) -> None:
    """
    Navigate up (KEY_UP).
    """
    _sc(ctx).up()


@cli.command("down")
def down(ctx: typer.Context) -> None:
    """
    Navigate down (KEY_DOWN).
    """
    _sc(ctx).down()


@cli.command("left")
def left(ctx: typer.Context) -> None:
    """
    Navigate left (KEY_LEFT).
    """
    _sc(ctx).left()


@cli.command("right")
def right(ctx: typer.Context) -> None:
    """
    Navigate right (KEY_RIGHT).
    """
    _sc(ctx).right()


@cli.command("enter")
def enter(ctx: typer.Context) -> None:
    """
    Confirm / enter (KEY_ENTER).
    """
    _sc(ctx).enter()


@cli.command("volume-up")
def volume_up(ctx: typer.Context) -> None:
    """
    Increase volume (KEY_VOLUP).
    """
    _sc(ctx).volume_up()


@cli.command("volume-down")
def volume_down(ctx: typer.Context) -> None:
    """
    Decrease volume (KEY_VOLDOWN).
    """
    _sc(ctx).volume_down()


@cli.command("mute")
def mute(ctx: typer.Context) -> None:
    """
    Toggle mute (KEY_MUTE).
    """
    _sc(ctx).mute()


@cli.command("channel-up")
def channel_up(ctx: typer.Context) -> None:
    """
    Channel up (KEY_CHUP).
    """
    _sc(ctx).channel_up()


@cli.command("channel-down")
def channel_down(ctx: typer.Context) -> None:
    """
    Channel down (KEY_CHDOWN).
    """
    _sc(ctx).channel_down()


@cli.command("channel")
def channel(
    ctx: typer.Context,
    ch: int = typer.Argument(..., help="Channel number"),
) -> None:
    """
    Change channel by number (KEY_0–KEY_9 + KEY_ENTER).
    """
    _sc(ctx).channel(ch)
