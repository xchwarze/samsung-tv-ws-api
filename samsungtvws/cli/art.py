"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2025 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

from __future__ import annotations

import json
import os
import random
import tempfile
from typing import Any
import urllib.parse
import urllib.request

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


def _download_url_to_temp_path(image_url: str) -> tuple[str, str]:
    parsed_url = urllib.parse.urlparse(image_url)
    _, url_extension = os.path.splitext(parsed_url.path)

    inferred_file_type = url_extension[1:].lower() if url_extension else "jpg"
    if inferred_file_type == "jpeg":
        inferred_file_type = "jpg"

    file_descriptor, temp_path = tempfile.mkstemp(
        prefix="samsungtvws-art-",
        suffix=f".{inferred_file_type}",
    )
    os.close(file_descriptor)

    request = urllib.request.Request(
        image_url,
        headers={"User-Agent": "samsungtvws-cli/1.0"},
        method="GET",
    )

    try:
        with (
            urllib.request.urlopen(request, timeout=60) as response,
            open(temp_path, "wb") as output_file,
        ):
            output_file.write(response.read())
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise

    return temp_path, inferred_file_type


def _state_file_path_for_folder(folder_path: str) -> str:
    return os.path.join(folder_path, ".samsungtvws-art-sync.json")


def _load_state_file(state_file_path: str) -> dict[str, Any]:
    if not os.path.isfile(state_file_path):
        return {"version": 1, "files": {}}

    try:
        with open(state_file_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"version": 1, "files": {}}

    files = data.get("files")
    if not isinstance(files, dict):
        files = {}

    return {"version": 1, "files": files}


def _save_state_file(state_file_path: str, state: dict[str, Any]) -> None:
    with open(state_file_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _file_fingerprint(path: str) -> dict[str, Any]:
    stat = os.stat(path)
    fingerprint: dict[str, Any] = {
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }
    return fingerprint


def _fingerprint_matches(cached: dict[str, Any], current: dict[str, Any]) -> bool:
    if cached.get("size") != current.get("size"):
        return False
    if cached.get("mtime_ns") != current.get("mtime_ns"):
        return False
    return True


def _cached_content_id(
    cached_files: dict[str, Any],
    image_path: str,
    fingerprint: dict[str, Any],
    *,
    refresh: bool,
) -> str | None:
    if refresh:
        return None
    cached_entry = cached_files.get(image_path)
    if not isinstance(cached_entry, dict):
        return None
    if not _fingerprint_matches(cached_entry, fingerprint):
        return None
    content_id = cached_entry.get("content_id")
    return content_id if isinstance(content_id, str) else None


def _iter_image_paths(
    root_dir: str, recursive: bool, allowed_extensions: set[str]
) -> list[str]:
    image_paths: list[str] = []

    if recursive:
        for directory_path, _, file_names in os.walk(root_dir):
            for file_name in file_names:
                _, ext = os.path.splitext(file_name)
                if ext[1:].lower() in allowed_extensions:
                    image_paths.append(os.path.join(directory_path, file_name))
    else:
        for file_name in os.listdir(root_dir):
            full_path = os.path.join(root_dir, file_name)
            if not os.path.isfile(full_path):
                continue
            _, ext = os.path.splitext(file_name)
            if ext[1:].lower() in allowed_extensions:
                image_paths.append(full_path)

    image_paths.sort()
    return image_paths


def _resolve_pick_mode(upload_all: bool, sync_all: bool, pick_random: bool) -> bool:
    if upload_all and sync_all:
        raise typer.BadParameter("Use either --upload-all or --sync-all, not both.")
    if upload_all and pick_random:
        raise typer.BadParameter("Use either --upload-all or --random, not both.")
    if sync_all and pick_random:
        raise typer.BadParameter("Use either --sync-all or --random, not both.")
    # Default mode: pick random if no explicit mode is chosen
    if not upload_all and not sync_all and not pick_random:
        return True
    return pick_random


def _resolve_show_flag(show: bool | None, pick_random: bool) -> bool:
    if show is not None:
        return show
    return bool(pick_random)


def _handle_random_pick(
    art: Any,
    image_paths: list[str],
    cached_files: dict[str, Any],
    refresh: bool,
    no_state: bool,
    resolved_state_file: str,
    state: dict[str, Any],
    upload_arguments: dict[str, Any],
    show_flag: bool,
) -> None:
    chosen_path = random.choice(image_paths)
    chosen_fingerprint = _file_fingerprint(chosen_path)

    cached_entry = cached_files.get(chosen_path)
    if (
        not refresh
        and isinstance(cached_entry, dict)
        and _fingerprint_matches(cached_entry, chosen_fingerprint)
        and isinstance(cached_entry.get("content_id"), str)
    ):
        content_id_to_display = cached_entry["content_id"]
        typer.echo(f"OK: cached {chosen_path} -> {content_id_to_display}")
    else:
        uploaded_content_id = art.upload(chosen_path, **upload_arguments)
        typer.echo(f"OK: uploaded {chosen_path} -> {uploaded_content_id}")

        if not no_state:
            cached_files[chosen_path] = {
                "content_id": uploaded_content_id,
                **chosen_fingerprint,
            }
            _save_state_file(resolved_state_file, state)

        content_id_to_display = uploaded_content_id

    art.select_image(content_id_to_display, show=show_flag)
    typer.echo(f"OK: displayed {content_id_to_display}")


@cli.command("art-supported")
def art_supported(ctx: typer.Context) -> None:
    """Check if Art Mode is supported (FrameTVSupport)."""
    tv = get_tv(ctx)
    typer.echo(str(tv.art().supported()))


@cli.command("art-mode")
def art_mode(
    ctx: typer.Context,
    on: bool | None = typer.Option(
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
    category: str | None = typer.Option(None, "--category", help="Category id filter"),
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
    out: str = typer.Option("", "--out", help="Output file path"),
    legacy: bool = typer.Option(
        False, "--legacy", help="Use legacy get_thumbnail instead of get_thumbnail_list"
    ),
) -> None:
    """Fetch thumbnail and write it to a file."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    art = tv.art()

    if legacy:
        thumbs: dict[str, bytearray] = art.get_thumbnail(content_id, as_dict=True)  # type: ignore[assignment]
    else:
        thumbs = art.get_thumbnail_list(content_id)

    if not thumbs:
        raise typer.Exit(code=1)

    name, data = next(iter(thumbs.items()))
    if not out:
        # default to the filename hinted by the TV when possible
        out = name

    with open(out, "wb") as f:
        f.write(bytes(data))

    typer.echo(f"OK: wrote {name} -> {out}")


@cli.command("art-upload")
def art_upload(
    ctx: typer.Context,
    file: str | None = typer.Argument(None, help="Path to image file"),
    url: str | None = typer.Option(
        None,
        "--url",
        help="Image URL to download and upload",
    ),
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
    file_type: str | None = typer.Option(
        None,
        "--file-type",
        help="Override file type (png/jpg/jpeg). If omitted, inferred from filename.",
    ),
) -> None:
    """Upload an image and print content_id."""
    _require_art_supported(ctx)

    if file is None and url is None:
        raise typer.BadParameter("Provide FILE or --url.")

    if file is not None and url is not None:
        raise typer.BadParameter("Use either a file path or --url, not both.")

    tv = get_tv(ctx)
    art = tv.art()

    upload_arguments = {
        "matte": matte,
        "portrait_matte": portrait_matte,
    }
    if file_type:
        upload_arguments["file_type"] = file_type

    temporary_path: str | None = None
    try:
        if url is not None:
            temporary_path, inferred_file_type = _download_url_to_temp_path(url)
            upload_path = temporary_path
            if file_type is None:
                upload_arguments["file_type"] = inferred_file_type
        else:
            assert file is not None
            upload_path = file
            if not os.path.exists(upload_path):
                raise typer.BadParameter(f"File not found: {upload_path}")

        content_id = art.upload(upload_path, **upload_arguments)
        typer.echo(f"OK: uploaded -> {content_id}")
    finally:
        if temporary_path:
            try:
                os.remove(temporary_path)
            except OSError:
                pass


@cli.command("art-sync")
def art_sync(
    ctx: typer.Context,
    folder: str = typer.Argument(..., help="Folder containing images"),
    upload_all: bool = typer.Option(
        False, "--upload-all", help="Upload all new/changed images"
    ),
    sync_all: bool = typer.Option(
        False,
        "--sync-all",
        help="Upload all new/changed images and delete missing ones from TV (requires state file)",
    ),
    pick_random: bool = typer.Option(
        False, "--random", help="Pick one image (default if no mode)"
    ),
    recursive: bool = typer.Option(
        True, "--recursive/--no-recursive", help="Scan subfolders"
    ),
    extensions: str = typer.Option(
        "jpg,jpeg,png", "--extensions", help="Comma-separated extensions"
    ),
    state_file: str = typer.Option("", "--state-file", help="Path to cache JSON file"),
    no_state: bool = typer.Option(
        False, "--no-state", help="Do not read/write cache file"
    ),
    refresh: bool = typer.Option(False, "--refresh", help="Ignore cache and re-upload"),
    show: bool | None = typer.Option(
        None, "--show/--no-show", help="Show when selecting"
    ),
    matte: str = typer.Option(
        "shadowbox_polar", "--matte", help="Matte id (use 'none' to disable)"
    ),
    portrait_matte: str = typer.Option(
        "shadowbox_polar",
        "--portrait-matte",
        help="Portrait matte id (use 'none' to disable)",
    ),
    file_type: str | None = typer.Option(
        None,
        "--file-type",
        help="Override file type (png/jpg/jpeg). If omitted, inferred from filename.",
    ),
) -> None:
    _require_art_supported(ctx)
    folder = os.path.abspath(folder)

    pick_random = _resolve_pick_mode(upload_all, sync_all, pick_random)

    if sync_all and no_state:
        raise typer.BadParameter(
            "--sync-all requires a state file (do not use --no-state)."
        )

    if not os.path.isdir(folder):
        raise typer.BadParameter(f"Folder not found: {folder}")

    allowed_extensions = {
        ext.strip().lower().lstrip(".") for ext in extensions.split(",") if ext.strip()
    }
    if not allowed_extensions:
        raise typer.BadParameter("No valid extensions provided.")

    resolved_state_file = ""
    if not no_state:
        resolved_state_file = state_file or _state_file_path_for_folder(folder)

    state = {"version": 1, "files": {}}
    if not no_state:
        state = _load_state_file(resolved_state_file)

    cached_files = state["files"]
    assert isinstance(cached_files, dict)

    tv = get_tv(ctx)
    art = tv.art()

    upload_arguments: dict[str, Any] = {
        "matte": matte,
        "portrait_matte": portrait_matte,
    }
    if file_type is not None:
        upload_arguments["file_type"] = file_type

    image_paths = _iter_image_paths(
        folder, recursive=recursive, allowed_extensions=allowed_extensions
    )
    if not image_paths and not sync_all:
        typer.echo("OK: no images found")
        raise typer.Exit(code=0)

    show_flag = _resolve_show_flag(show, pick_random)

    if pick_random:
        _handle_random_pick(
            art=art,
            image_paths=image_paths,
            cached_files=cached_files,
            refresh=refresh,
            no_state=no_state,
            resolved_state_file=resolved_state_file,
            state=state,
            upload_arguments=upload_arguments,
            show_flag=show_flag,
        )
        return

    # --sync-all: delete entries that exist in cache but no longer exist on disk
    deleted_count = 0
    delete_failed_count = 0
    if sync_all:
        # Iterate over a snapshot since we may mutate cached_files
        for cached_path, cached_entry in list(cached_files.items()):
            if os.path.exists(cached_path):
                continue
            content_id = None
            if isinstance(cached_entry, dict):
                cid = cached_entry.get("content_id")
                if isinstance(cid, str):
                    content_id = cid

            if content_id:
                ok = art.delete(content_id)
                if not ok:
                    delete_failed_count += 1
                    typer.echo(
                        f"ERROR: failed to delete missing {cached_path} -> {content_id}",
                        err=True,
                    )
                    continue
                typer.echo(f"OK: deleted missing {cached_path} -> {content_id}")
                deleted_count += 1

            # Remove from cache even if there was no content_id
            cached_files.pop(cached_path, None)

    uploaded_count = 0
    skipped_count = 0

    for image_path in image_paths:
        fingerprint = _file_fingerprint(image_path)
        existing_id = _cached_content_id(
            cached_files,
            image_path,
            fingerprint,
            refresh=refresh,
        )
        if existing_id is not None:
            skipped_count += 1
            continue

        uploaded_content_id = art.upload(image_path, **upload_arguments)
        uploaded_count += 1
        typer.echo(f"OK: uploaded {image_path} -> {uploaded_content_id}")

        if not no_state:
            cached_files[image_path] = {
                "content_id": uploaded_content_id,
                **fingerprint,
            }

    if not no_state:
        _save_state_file(resolved_state_file, state)

    if sync_all:
        typer.echo(
            f"OK: done (uploaded={uploaded_count}, skipped={skipped_count}, deleted={deleted_count})"
        )
        if delete_failed_count:
            raise typer.Exit(code=1)
        return

    typer.echo(f"OK: done (uploaded={uploaded_count}, skipped={skipped_count})")


@cli.command("art-delete")
def art_delete(
    ctx: typer.Context,
    content_id: str = typer.Argument(..., help="Content id"),
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
    content_ids: list[str] = typer.Argument(..., help="Content ids"),  # noqa: B008
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
    portrait_matte: str | None = typer.Option(
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
    """Get slideshow status (falls back to legacy auto-rotation status)."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    art = tv.art()
    try:
        typer.echo(str(art.get_slideshow_status()))
    except exceptions.ResponseError:
        typer.echo(str(art.get_auto_rotation_status()))


@cli.command("art-slideshow-set")
def art_slideshow_set(
    ctx: typer.Context,
    category_id: str = typer.Option(
        ...,
        "--category-id",
        help="Category id as reported by the TV (e.g. MY-C0004)",
    ),
    duration: int = typer.Option(
        0,
        "--duration",
        min=0,
        help="Minutes (>0) or 0 to disable",
    ),
    shuffle: bool = typer.Option(
        True,
        "--shuffle/--ordered",
        help="Shuffle slideshow items",
    ),
) -> None:
    """
    Set slideshow / auto-rotation status.

    Uses the new slideshow API when available, falls back to legacy
    auto-rotation API on older TVs.
    """
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    art = tv.art()

    try:
        # New API
        result = art.set_slideshow_status(
            duration=duration,
            type=shuffle,
            category_id=category_id,
        )
    except exceptions.ResponseError:
        # Legacy API
        result = art.set_auto_rotation_status(
            duration=duration,
            type=shuffle,
            category_id=category_id,
        )

    typer.echo(str(result))


@cli.command("art-categories")
def art_categories(ctx: typer.Context) -> None:
    """List raw category items as returned by the Art API."""
    _require_art_supported(ctx)
    tv = get_tv(ctx)
    for item in tv.art().available():
        typer.echo(json.dumps(item, ensure_ascii=False))
