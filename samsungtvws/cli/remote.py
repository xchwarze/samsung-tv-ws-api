"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2025 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

from __future__ import annotations

import typer

from .main import cli, get_tv


def _normalize_cmd(cmd: str) -> str:
    """
    Normalize remote key command to protocol values.
    """
    c = cmd.strip().lower()
    if c in {"click", "press", "release"}:
        return c.capitalize()
    raise typer.BadParameter("Invalid --cmd. Use: Click|Press|Release")


@cli.command("send-key")
def send_key(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="KEY_* value"),
    times: int = typer.Option(1, "--times", min=1, help="Repeat count"),
    cmd: str = typer.Option("Click", "--cmd", help="Click|Press|Release"),
    delay: float | None = typer.Option(
        None,
        "--delay",
        min=0.0,
        help="Override key press delay (seconds)",
    ),
) -> None:
    """
    Send a raw remote key.
    """
    tv = get_tv(ctx)
    tv.send_key(
        key=key,
        times=times,
        cmd=_normalize_cmd(cmd),
        key_press_delay=delay,
    )


@cli.command("hold-key")
def hold_key(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="KEY_* value"),
    seconds: float = typer.Argument(..., min=0.0, help="Hold duration (seconds)"),
) -> None:
    """
    Hold a key for N seconds (Press -> sleep -> Release).
    """
    get_tv(ctx).hold_key(key, seconds)


@cli.command("move-cursor")
def move_cursor(
    ctx: typer.Context,
    x: int = typer.Argument(..., help="X coordinate"),
    y: int = typer.Argument(..., help="Y coordinate"),
) -> None:
    """
    Move TV cursor (mouse device).
    """
    get_tv(ctx).move_cursor(x, y)


@cli.command("mouse-click")
def mouse_click(ctx: typer.Context) -> None:
    """Mouse click (KEY_ENTER)."""
    get_tv(ctx).send_key("KEY_ENTER")


@cli.command("factory")
def factory(
    ctx: typer.Context,
    i_know_what_im_doing: bool = typer.Option(
        False,
        "--i-know-what-im-doing",
        help="Acknowledge dangerous operation (KEY_FACTORY)",
    ),
) -> None:
    """
    Open factory/service menu (KEY_FACTORY).
    """
    if not i_know_what_im_doing:
        typer.echo(
            "ERROR: This command sends KEY_FACTORY and may damage your TV.\n"
            "Re-run with --i-know-what-im-doing to proceed.",
            err=True,
        )
        raise typer.Exit(code=1)

    get_tv(ctx).send_key("KEY_FACTORY")


@cli.command("send-text")
def send_text(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to send (UTF-8)"),
    end: bool = typer.Option(
        False,
        "--end",
        help="Also send input end (SendInputEnd) after text",
    ),
) -> None:
    """
    Send text to the TV input (IME).
    """
    tv = get_tv(ctx)
    tv.send_text(text)
    if end:
        tv.end_text()


@cli.command("end-text")
def end_text(ctx: typer.Context) -> None:
    """
    End current text input session (SendInputEnd).
    """
    get_tv(ctx).end_text()
