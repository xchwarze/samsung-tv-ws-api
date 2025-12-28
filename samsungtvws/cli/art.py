"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2025 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

from __future__ import annotations

import os
from typing import Optional

import typer

from samsungtvws import exceptions

from .main import cli, get_tv


def _require_art_supported(ctx: typer.Context) -> None:
    tv = get_tv(ctx)
    if not tv.art().supported():
        typer.echo(
            "ERROR: Art Mode not supported on this TV (FrameTVSupport=false).", err=True
        )
        raise typer.Exit(code=2)


@cli.command("art-supported")
def art_supported(ctx: typer.Context) -> None:
    """Check if Art Mode is supported (FrameTVSupport)."""
    tv = get_tv(ctx)
    typer.echo(str(tv.art().supported()))


@cli.command("art-mode")
def art_mode(
    ctx: typer.Context,
    on: Optional[bool] = typer.Option(
        None,
        "--on/--off",
        help="Set Art Mode state",
    ),
) -> None:
    """Get or set Art Mode state."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    art = tv.art()

    if on is None:
        typer.echo(str(art.get_artmode()))
        return

    typer.echo(str(art.set_artmode(on)))


@cli.command("art-api-version")
def art_api_version(ctx: typer.Context) -> None:
    """Get Art API version."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    typer.echo(tv.art().get_api_version())


@cli.command("art-current")
def art_current(ctx: typer.Context) -> None:
    """Get currently selected artwork info."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    typer.echo(str(tv.art().get_current()))


@cli.command("art-available")
def art_available(
    ctx: typer.Context,
    category: Optional[str] = typer.Option(
        None, "--category", help="Category id filter"
    ),
) -> None:
    """List available art content."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    typer.echo(str(tv.art().available(category=category)))


@cli.command("art-display")
def art_display(
    ctx: typer.Context,
    content_id: str = typer.Argument(..., help="Content id"),
    show: bool = typer.Option(True, "--show/--no-show", help="Show immediately"),
) -> None:
    """Select an artwork by content id."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    typer.echo(str(tv.art().select_image(content_id, show=show)))


@cli.command("art-thumbnail")
def art_thumbnail(
    ctx: typer.Context,
    content_id: str = typer.Argument(..., help="Content id"),
    out: str = typer.Option(
        "", "--out", help="Output file path (defaults to <content_id>.jpg)"
    ),
    legacy: bool = typer.Option(
        False, "--legacy", help="Use legacy get_thumbnail instead of get_thumbnail_list"
    ),
) -> None:
    """Fetch thumbnail and write it to a file."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    art = tv.art()

    if legacy:
        thumbs = art.get_thumbnail(content_id, as_dict=True)
    else:
        thumbs = art.get_thumbnail_list(content_id)

    if not thumbs:
        raise typer.Exit(code=1)

    name, data = next(iter(thumbs.items()))
    if not out:
        # best-effort default
        out = f"{content_id}.jpg"

    with open(out, "wb") as f:
        f.write(bytes(data))

    typer.echo(f"OK: wrote {name} -> {out}")


@cli.command("art-upload")
def art_upload(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="Path to image file"),
    matte: str = typer.Option(
        "shadowbox_polar",
        "--matte",
        help="Matte id (use 'none' to disable)",
    ),
    portrait_matte: str = typer.Option(
        "shadowbox_polar",
        "--portrait-matte",
        help="Portrait matte id (use 'none' to disable)",
    ),
    file_type: Optional[str] = typer.Option(
        None,
        "--file-type",
        help="Override file type (png/jpg/jpeg). If omitted, inferred from filename.",
    ),
) -> None:
    """Upload an image and print content_id (without extension)."""
    _require_art_supported(ctx)

    if not os.path.exists(file):
        raise typer.BadParameter(f"File not found: {file}")

    tv = get_tv(ctx)
    art = tv.art()

    kwargs = {
        "matte": matte,
        "portrait_matte": portrait_matte,
    }
    if file_type:
        kwargs["file_type"] = file_type

    content_id = art.upload(file, **kwargs)
    typer.echo(os.path.splitext(content_id)[0])


@cli.command("art-delete")
def art_delete(
    ctx: typer.Context,
    content_id: str = typer.Argument(..., help="Content id (without extension)"),
) -> None:
    """Delete an artwork by content id."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    ok = tv.art().delete(content_id)
    if not ok:
        raise typer.Exit(code=1)
    typer.echo("OK")


@cli.command("art-delete-list")
def art_delete_list(
    ctx: typer.Context,
    content_ids: list[str] = typer.Argument(
        ..., help="Content ids (without extension)"
    ),
) -> None:
    """Delete multiple artworks by content id."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    ok = tv.art().delete_list(content_ids)
    if not ok:
        raise typer.Exit(code=1)
    typer.echo("OK")


@cli.command("art-matte-list")
def art_matte_list(ctx: typer.Context) -> None:
    """List available matte types/colors."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    typer.echo(str(tv.art().get_matte_list()))


@cli.command("art-matte-set")
def art_matte_set(
    ctx: typer.Context,
    content_id: str = typer.Argument(..., help="Artwork content id"),
    matte_id: str = typer.Argument(
        ..., help="Matte id (e.g. none, shadowbox_polar, ...)"
    ),
    portrait_matte: Optional[str] = typer.Option(
        None,
        "--portrait-matte",
        help="Portrait matte id (optional)",
    ),
) -> None:
    """Change matte for an artwork."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    typer.echo(
        str(tv.art().change_matte(content_id, matte_id, portrait_matte=portrait_matte))
    )


@cli.command("art-photo-filters")
def art_photo_filters(ctx: typer.Context) -> None:
    """List available photo filters."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    typer.echo(str(tv.art().get_photo_filter_list()))


@cli.command("art-photo-filter-set")
def art_photo_filter_set(
    ctx: typer.Context,
    content_id: str = typer.Argument(..., help="Artwork content id"),
    filter_id: str = typer.Argument(..., help="Filter id (e.g. ink, ...)"),
) -> None:
    """Apply a photo filter to a specific artwork."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    typer.echo(str(tv.art().set_photo_filter(content_id, filter_id)))


@cli.command("art-slideshow-status")
def art_slideshow_status(ctx: typer.Context) -> None:
    """Get slideshow status (new API) or auto-rotation status (legacy)."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    art = tv.art()
    try:
        typer.echo(str(art.get_slideshow_status()))
    except exceptions.ResponseError:
        typer.echo(str(art.get_auto_rotation_status()))
