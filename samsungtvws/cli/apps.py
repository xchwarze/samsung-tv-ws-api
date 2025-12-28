"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2025 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import typer

from .main import cli, get_tv


@cli.command("apps")
def list_apps(ctx: typer.Context) -> None:
    """
    List installed apps (not available on all TVs).
    """
    data = get_tv(ctx).app_list()
    typer.echo(str(data))


@cli.command("app-run-ws")
def run_app(
    ctx: typer.Context,
    app_id: str = typer.Argument(..., help="App ID"),
    app_type: str = typer.Option(
        "DEEP_LINK",
        "--type",
        help="DEEP_LINK|NATIVE_LAUNCH",
    ),
    meta_tag: str = typer.Option(
        "",
        "--meta-tag",
        help="Meta tag / deep link payload",
    ),
) -> None:
    """
    Launch an app by ID (not available on all TVs).
    """
    get_tv(ctx).run_app(app_id, app_type=app_type, meta_tag=meta_tag)


@cli.command("open-browser")
def open_browser(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="URL to open in TV browser"),
) -> None:
    """
    Open a URL in the TV browser app (not available on all TVs).
    """
    get_tv(ctx).open_browser(url)
