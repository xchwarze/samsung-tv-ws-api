"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2025 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import typer
from .main import cli, get_tv


@cli.command("device-info")
def device_info(ctx: typer.Context) -> None:
    """
    Get device information (model, name, features).
    """
    tv = get_tv(ctx)
    typer.echo(str(tv.rest_device_info()))


@cli.command("app-status")
def app_status(
    ctx: typer.Context,
    app_id: str = typer.Argument(..., help="App ID"),
) -> None:
    """
    Get application status.
    """
    tv = get_tv(ctx)
    typer.echo(str(tv.rest_app_status(app_id)))


@cli.command("app-run")
def app_run(
    ctx: typer.Context,
    app_id: str = typer.Argument(..., help="App ID"),
) -> None:
    """
    Run application via REST API.
    """
    tv = get_tv(ctx)
    typer.echo(str(tv.rest_app_run(app_id)))


@cli.command("app-close")
def app_close(
    ctx: typer.Context,
    app_id: str = typer.Argument(..., help="App ID"),
) -> None:
    """
    Close application via REST API.
    """
    tv = get_tv(ctx)
    typer.echo(str(tv.rest_app_close(app_id)))


@cli.command("app-install")
def app_install(
    ctx: typer.Context,
    app_id: str = typer.Argument(..., help="App ID"),
) -> None:
    """
    Install application from official store.
    """
    tv = get_tv(ctx)
    typer.echo(str(tv.rest_app_install(app_id)))

