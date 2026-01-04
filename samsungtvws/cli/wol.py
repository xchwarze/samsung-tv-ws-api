"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2025 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import typer
import wakeonlan

from .main import cli


@cli.command("wol")
def wol(
    mac: str = typer.Argument(..., help="TV MAC address"),
    port: int = typer.Option(9, "--wol-port", help="WOL UDP port"),
) -> None:
    """Send Wake-on-LAN magic packet."""
    wakeonlan.send_magic_packet(mac, port=port)
    typer.echo(f"OK: magic packet sent to {mac}")
