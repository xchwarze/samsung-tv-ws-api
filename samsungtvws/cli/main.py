"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2025 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import logging
from typing import List, Optional

import typer
from typer.core import TyperGroup

from samsungtvws import SamsungTVWS


# this helper is for typer to list the commands correctly
class SortedTyperGroup(TyperGroup):
    def list_commands(self, ctx: typer.Context) -> List[str]:
        return sorted(self.commands)


def setup_logging(verbose: int) -> None:
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def get_tv(ctx: typer.Context) -> SamsungTVWS:
    cfg = ctx.obj
    return SamsungTVWS(
        host=cfg["host"],
        port=cfg["port"],
        token=cfg["token"],
        token_file=cfg["token_file"],
        timeout=cfg["timeout"],
        key_press_delay=cfg["key_press_delay"],
        name=cfg["name"],
    )


def bootstrap_token_if_needed(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        return

    if not ctx.obj.get("print_token", True):
        return

    if ctx.obj.get("token_file") is not None:
        return

    if ctx.obj.get("token") is not None:
        return

    tv = get_tv(ctx)
    try:
        tv.open()
        if tv.token:
            ctx.obj["token"] = tv.token
            typer.echo(f"[*] Auth token (not saved): {tv.token}", err=True)
    finally:
        tv.close()


#  It's Magic! https://www.youtube.com/watch?v=WF6xdRTheDo
cli = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    cls=SortedTyperGroup,
)


@cli.callback()
def main(
    ctx: typer.Context,
    host: str = typer.Option(..., "--host", help="TV IP/host"),
    port: int = typer.Option(8002, "--port", help="Websocket port (8001/8002)"),
    token: Optional[str] = typer.Option(None, "--token", help="Auth token"),
    token_file: Optional[str] = typer.Option(
        None, "--token-file", help="Path to token file"
    ),
    timeout: Optional[float] = typer.Option(
        10, "--timeout", help="Socket timeout seconds (0 disables timeout)"
    ),
    key_press_delay: float = typer.Option(
        1.0, "--key-press-delay", help="Delay between key presses (seconds)"
    ),
    name: str = typer.Option(
        "SamsungTvRemoteCli", "--name", help="Client name shown on TV"
    ),
    print_token: bool = typer.Option(
        True,
        "--print-token/--no-print-token",
        help="Print token once if it is not saved",
    ),
    verbose: int = typer.Option(
        0,
        "-v",
        "--verbose",
        count=True,
        help="Increase verbosity (-v: INFO, -vv: DEBUG)",
    ),
) -> None:
    """
    Samsung TV CLI - by xchwarze
    """
    setup_logging(verbose)

    # Preserve SDK semantics: timeout=0 => None
    normalized_timeout = None if timeout == 0 else timeout

    ctx.obj = {
        "host": host,
        "port": port,
        "token": token,
        "token_file": token_file,
        "print_token": print_token,
        "timeout": normalized_timeout,
        "key_press_delay": key_press_delay,
        "name": name,
    }
    bootstrap_token_if_needed(ctx)
