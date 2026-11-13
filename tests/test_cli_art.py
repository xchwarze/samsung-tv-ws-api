"""Tests for the art CLI commands."""

from __future__ import annotations

from collections.abc import Iterator
import io
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from unittest.mock import Mock, _Call, call, patch

import pytest
from typer.testing import CliRunner

from samsungtvws import exceptions
from samsungtvws.art import SamsungTVArt
from samsungtvws.cli import cli

BASE_ARGS = ["--host", "127.0.0.1", "--token", "abc"]
STATE_FILE_NAME = ".samsungtvws-art-sync.json"

runner = CliRunner()

# CI forces rich terminal output: colored and wrapped in a box
_RICH_MARKUP = re.compile(r"\x1b\[[0-9;]*m|[\u2500-\u257f]")


@pytest.fixture(name="art")
def mock_art() -> Iterator[Mock]:
    """Patch SamsungTVWS used by the CLI and return its art API mock."""
    art = Mock(spec=SamsungTVArt)
    art.supported.return_value = True
    with patch("samsungtvws.cli.main.SamsungTVWS") as tv_class:
        tv_class.return_value.art.return_value = art
        yield art


def invoke(*args: str) -> Any:
    """Run the CLI with the base connection options."""
    return runner.invoke(cli, [*BASE_ARGS, *args])


def plain_text(text: str) -> str:
    """Return CLI output without rich markup, on a single line."""
    return " ".join(_RICH_MARKUP.sub("", text).split())


def write_image(path: Path, data: bytes = b"img") -> str:
    """Create an image file and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def fingerprint(path: str) -> dict[str, int]:
    """Return the size/mtime fingerprint the CLI stores for a file."""
    stat = os.stat(path)
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def fake_response(data: bytes) -> io.BytesIO:
    """Build a urlopen-like context manager returning data."""
    return io.BytesIO(data)


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["art-mode"], id="art-mode"),
        pytest.param(["art-api-version"], id="art-api-version"),
        pytest.param(["art-current"], id="art-current"),
        pytest.param(["art-available"], id="art-available"),
        pytest.param(["art-display", "MY_F0001"], id="art-display"),
        pytest.param(["art-thumbnail", "MY_F0001"], id="art-thumbnail"),
        pytest.param(["art-upload", "x.jpg"], id="art-upload"),
        pytest.param(["art-sync", "."], id="art-sync"),
        pytest.param(["art-delete", "MY_F0001"], id="art-delete"),
        pytest.param(["art-delete-list", "MY_F0001"], id="art-delete-list"),
        pytest.param(["art-matte-list"], id="art-matte-list"),
        pytest.param(["art-matte-set", "MY_F0001", "none"], id="art-matte-set"),
        pytest.param(["art-photo-filters"], id="art-photo-filters"),
        pytest.param(["art-photo-filter-set", "MY_F0001", "ink"], id="filter-set"),
        pytest.param(["art-slideshow-status"], id="art-slideshow-status"),
        pytest.param(["art-slideshow-set", "--category-id", "X"], id="slideshow-set"),
        pytest.param(["art-categories"], id="art-categories"),
    ],
)
def test_art_not_supported(art: Mock, args: list[str]) -> None:
    """Commands requiring Art Mode exit with code 2 when unsupported."""
    art.supported.return_value = False

    result = invoke(*args)

    assert result.exit_code == 2
    assert "Art Mode not supported" in result.stderr
    art.upload.assert_not_called()


@pytest.mark.parametrize(
    ("args", "method", "return_value", "expected_call", "expected_output"),
    [
        pytest.param(
            ["art-supported"], "supported", True, call(), "True\n", id="art-supported"
        ),
        pytest.param(
            ["art-mode"], "get_artmode", "on", call(), "on\n", id="art-mode-get"
        ),
        pytest.param(
            ["art-mode", "--on"],
            "set_artmode",
            None,
            call(True),
            "None\n",
            id="art-mode-on",
        ),
        pytest.param(
            ["art-mode", "--off"],
            "set_artmode",
            None,
            call(False),
            "None\n",
            id="art-mode-off",
        ),
        pytest.param(
            ["art-api-version"],
            "get_api_version",
            "2.03",
            call(),
            "2.03\n",
            id="art-api-version",
        ),
        pytest.param(
            ["art-current"],
            "get_current",
            {"content_id": "MY_F0001"},
            call(),
            "{'content_id': 'MY_F0001'}\n",
            id="art-current",
        ),
        pytest.param(
            ["art-available"],
            "available",
            [],
            call(category=None),
            "[]\n",
            id="art-available",
        ),
        pytest.param(
            ["art-available", "--category", "MY-C0002"],
            "available",
            [{"content_id": "MY_F0001"}],
            call(category="MY-C0002"),
            "[{'content_id': 'MY_F0001'}]\n",
            id="art-available-category",
        ),
        pytest.param(
            ["art-display", "MY_F0001"],
            "select_image",
            None,
            call("MY_F0001", show=True),
            "None\n",
            id="art-display",
        ),
        pytest.param(
            ["art-display", "MY_F0001", "--no-show"],
            "select_image",
            None,
            call("MY_F0001", show=False),
            "None\n",
            id="art-display-no-show",
        ),
        pytest.param(
            ["art-delete", "MY_F0001"],
            "delete",
            True,
            call("MY_F0001"),
            "OK\n",
            id="art-delete",
        ),
        pytest.param(
            ["art-delete-list", "MY_F0001", "MY_F0002"],
            "delete_list",
            True,
            call(["MY_F0001", "MY_F0002"]),
            "OK\n",
            id="art-delete-list",
        ),
        pytest.param(
            ["art-matte-list"],
            "get_matte_list",
            [{"matte_type": "none"}],
            call(),
            "[{'matte_type': 'none'}]\n",
            id="art-matte-list",
        ),
        pytest.param(
            ["art-matte-set", "MY_F0001", "shadowbox_polar"],
            "change_matte",
            None,
            call("MY_F0001", "shadowbox_polar", portrait_matte=None),
            "None\n",
            id="art-matte-set",
        ),
        pytest.param(
            ["art-matte-set", "MY_F0001", "none", "--portrait-matte", "flexible"],
            "change_matte",
            None,
            call("MY_F0001", "none", portrait_matte="flexible"),
            "None\n",
            id="art-matte-set-portrait",
        ),
        pytest.param(
            ["art-photo-filters"],
            "get_photo_filter_list",
            ["ink"],
            call(),
            "['ink']\n",
            id="art-photo-filters",
        ),
        pytest.param(
            ["art-photo-filter-set", "MY_F0001", "ink"],
            "set_photo_filter",
            None,
            call("MY_F0001", "ink"),
            "None\n",
            id="art-photo-filter-set",
        ),
        pytest.param(
            ["art-slideshow-status"],
            "get_slideshow_status",
            {"value": "off"},
            call(),
            "{'value': 'off'}\n",
            id="art-slideshow-status",
        ),
        pytest.param(
            ["art-slideshow-set", "--category-id", "MY-C0004"],
            "set_slideshow_status",
            {"value": "0"},
            call(duration=0, type=True, category_id="MY-C0004"),
            "{'value': '0'}\n",
            id="art-slideshow-set",
        ),
        pytest.param(
            [
                "art-slideshow-set",
                "--category-id",
                "MY-C0004",
                "--duration",
                "15",
                "--ordered",
            ],
            "set_slideshow_status",
            {"value": "15"},
            call(duration=15, type=False, category_id="MY-C0004"),
            "{'value': '15'}\n",
            id="art-slideshow-set-ordered",
        ),
    ],
)
def test_simple_commands(
    art: Mock,
    args: list[str],
    method: str,
    return_value: Any,
    expected_call: _Call,
    expected_output: str,
) -> None:
    """Thin wrapper commands call the matching art method and print the result."""
    getattr(art, method).return_value = return_value

    result = invoke(*args)

    assert result.exit_code == 0
    assert result.output == expected_output
    assert getattr(art, method).mock_calls == [expected_call]


@pytest.mark.parametrize(
    ("args", "method"),
    [
        pytest.param(["art-delete", "MY_F0001"], "delete", id="art-delete"),
        pytest.param(
            ["art-delete-list", "MY_F0001"], "delete_list", id="art-delete-list"
        ),
    ],
)
def test_delete_failure(art: Mock, args: list[str], method: str) -> None:
    """Delete commands exit with code 1 when the TV reports failure."""
    getattr(art, method).return_value = False

    result = invoke(*args)

    assert result.exit_code == 1
    assert result.output == ""


def test_slideshow_status_legacy_fallback(art: Mock) -> None:
    """Slideshow status falls back to the legacy auto-rotation API."""
    art.get_slideshow_status.side_effect = exceptions.ResponseError("unsupported")
    art.get_auto_rotation_status.return_value = {"value": "off"}

    result = invoke("art-slideshow-status")

    assert result.exit_code == 0
    assert result.output == "{'value': 'off'}\n"


def test_slideshow_set_legacy_fallback(art: Mock) -> None:
    """Slideshow set falls back to the legacy auto-rotation API."""
    art.set_slideshow_status.side_effect = exceptions.ResponseError("unsupported")
    art.set_auto_rotation_status.return_value = {"value": "3"}

    result = invoke("art-slideshow-set", "--category-id", "MY-C0004", "--duration", "3")

    assert result.exit_code == 0
    assert result.output == "{'value': '3'}\n"
    art.set_auto_rotation_status.assert_called_once_with(
        duration=3, type=True, category_id="MY-C0004"
    )


def test_categories(art: Mock) -> None:
    """Categories prints one JSON line per available item."""
    art.available.return_value = [
        {"content_id": "MY_F0001", "category_id": "MY-C0002"},
        {"content_id": "SAM-S0001", "title": "Café"},
    ]

    result = invoke("art-categories")

    assert result.exit_code == 0
    assert result.output.splitlines() == [
        '{"content_id": "MY_F0001", "category_id": "MY-C0002"}',
        '{"content_id": "SAM-S0001", "title": "Café"}',
    ]


@pytest.mark.parametrize(
    ("extra_args", "method", "expected_call"),
    [
        pytest.param([], "get_thumbnail_list", ("MY_F0001",), id="list"),
        pytest.param(
            ["--legacy"],
            "get_thumbnail",
            ("MY_F0001",),
            id="legacy",
        ),
    ],
)
def test_thumbnail_to_out_file(
    art: Mock,
    tmp_path: Path,
    extra_args: list[str],
    method: str,
    expected_call: tuple[str, ...],
) -> None:
    """Thumbnail data is written to the --out path."""
    getattr(art, method).return_value = {"MY_F0001.jpg": bytearray(b"thumb")}
    out = tmp_path / "out.jpg"

    result = invoke("art-thumbnail", "MY_F0001", "--out", str(out), *extra_args)

    assert result.exit_code == 0
    assert result.output == f"OK: wrote MY_F0001.jpg -> {out}\n"
    assert out.read_bytes() == b"thumb"
    assert getattr(art, method).call_args.args == expected_call


def test_thumbnail_legacy_as_dict(art: Mock, tmp_path: Path) -> None:
    """Legacy thumbnail is requested as a dict."""
    art.get_thumbnail.return_value = {"a.png": bytearray(b"x")}

    invoke("art-thumbnail", "MY_F0001", "--legacy", "--out", str(tmp_path / "a"))

    art.get_thumbnail.assert_called_once_with("MY_F0001", as_dict=True)


def test_thumbnail_default_out_name(
    art: Mock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --out the thumbnail is written to the TV-provided file name."""
    monkeypatch.chdir(tmp_path)
    art.get_thumbnail_list.return_value = {"MY_F0001.png": bytearray(b"png")}

    result = invoke("art-thumbnail", "MY_F0001")

    assert result.exit_code == 0
    assert result.output == "OK: wrote MY_F0001.png -> MY_F0001.png\n"
    assert (tmp_path / "MY_F0001.png").read_bytes() == b"png"


def test_thumbnail_empty(art: Mock) -> None:
    """An empty thumbnail response exits with code 1."""
    art.get_thumbnail_list.return_value = {}

    result = invoke("art-thumbnail", "MY_F0001")

    assert result.exit_code == 1
    assert result.output == ""


@pytest.mark.parametrize(
    ("extra_args", "expected_kwargs"),
    [
        pytest.param(
            [],
            {"matte": "shadowbox_polar", "portrait_matte": "shadowbox_polar"},
            id="defaults",
        ),
        pytest.param(
            ["--matte", "none", "--portrait-matte", "flexible", "--file-type", "png"],
            {"matte": "none", "portrait_matte": "flexible", "file_type": "png"},
            id="custom",
        ),
    ],
)
def test_upload_file(
    art: Mock,
    tmp_path: Path,
    extra_args: list[str],
    expected_kwargs: dict[str, str],
) -> None:
    """A local file is uploaded and its content id printed."""
    image = write_image(tmp_path / "photo.jpg")
    art.upload.return_value = "MY_F0010"

    result = invoke("art-upload", image, *extra_args)

    assert result.exit_code == 0
    assert result.output == "OK: uploaded -> MY_F0010\n"
    art.upload.assert_called_once_with(image, **expected_kwargs)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        pytest.param(["art-upload"], "Provide FILE or --url.", id="none"),
        pytest.param(
            ["art-upload", "a.jpg", "--url", "http://example.com/a.jpg"],
            "Use either a file path or --url, not both.",
            id="both",
        ),
        pytest.param(
            ["art-upload", "/nonexistent/a.jpg"],
            "File not found: /nonexistent/a.jpg",
            id="missing-file",
        ),
    ],
)
def test_upload_bad_parameter(art: Mock, args: list[str], message: str) -> None:
    """Invalid upload arguments are rejected without uploading."""
    result = invoke(*args)

    assert result.exit_code == 2
    assert message in plain_text(result.stderr)
    art.upload.assert_not_called()


@pytest.mark.parametrize(
    ("url", "extra_args", "expected_file_type"),
    [
        pytest.param("http://example.com/a.PNG", [], "png", id="png"),
        pytest.param("http://example.com/a.jpeg", [], "jpg", id="jpeg"),
        pytest.param("http://example.com/image", [], "jpg", id="no-extension"),
        pytest.param(
            "http://example.com/a.png", ["--file-type", "jpg"], "jpg", id="override"
        ),
    ],
)
def test_upload_url(
    art: Mock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    extra_args: list[str],
    expected_file_type: str,
) -> None:
    """A URL is downloaded to a temp file, uploaded and the temp file removed."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    uploaded: dict[str, Any] = {}

    def _upload(path: str, **kwargs: Any) -> str:
        uploaded["data"] = Path(path).read_bytes()
        uploaded["path"] = path
        uploaded["kwargs"] = kwargs
        return "MY_F0011"

    art.upload.side_effect = _upload

    with patch(
        "samsungtvws.cli.art.urllib.request.urlopen",
        return_value=fake_response(b"downloaded"),
    ) as urlopen:
        result = invoke("art-upload", "--url", url, *extra_args)

    assert result.exit_code == 0
    assert result.output == "OK: uploaded -> MY_F0011\n"
    assert uploaded["data"] == b"downloaded"
    assert uploaded["kwargs"]["file_type"] == expected_file_type
    assert not os.path.exists(uploaded["path"])
    request = urlopen.call_args.args[0]
    assert request.full_url == url
    assert request.get_header("User-agent") == "samsungtvws-cli/1.0"
    assert urlopen.call_args.kwargs == {"timeout": 60}


def test_upload_url_temp_already_removed(
    art: Mock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A temp file that is already gone after upload does not raise."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    def _upload(path: str, **kwargs: Any) -> str:
        os.remove(path)
        return "MY_F0012"

    art.upload.side_effect = _upload

    with patch(
        "samsungtvws.cli.art.urllib.request.urlopen",
        return_value=fake_response(b"x"),
    ):
        result = invoke("art-upload", "--url", "http://example.com/a.jpg")

    assert result.exit_code == 0
    assert result.output == "OK: uploaded -> MY_F0012\n"
    assert list(tmp_path.iterdir()) == []


def test_upload_url_download_error(
    art: Mock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed download removes the temp file and propagates the error."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    with patch(
        "samsungtvws.cli.art.urllib.request.urlopen",
        side_effect=OSError("boom"),
    ):
        result = invoke("art-upload", "--url", "http://example.com/a.jpg")

    assert isinstance(result.exception, OSError)
    assert list(tmp_path.iterdir()) == []
    art.upload.assert_not_called()


def test_upload_url_download_error_temp_already_removed(
    art: Mock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed download whose temp file is already gone still propagates."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    def _urlopen(*args: Any, **kwargs: Any) -> io.BytesIO:
        for leftover in tmp_path.iterdir():
            leftover.unlink()
        raise OSError("boom")

    with patch("samsungtvws.cli.art.urllib.request.urlopen", side_effect=_urlopen):
        result = invoke("art-upload", "--url", "http://example.com/a.jpg")

    assert isinstance(result.exception, OSError)
    assert str(result.exception) == "boom"
    art.upload.assert_not_called()


@pytest.mark.parametrize(
    ("flags", "message"),
    [
        pytest.param(
            ["--upload-all", "--sync-all"],
            "Use either --upload-all or --sync-all, not both.",
            id="upload-all-sync-all",
        ),
        pytest.param(
            ["--upload-all", "--random"],
            "Use either --upload-all or --random, not both.",
            id="upload-all-random",
        ),
        pytest.param(
            ["--sync-all", "--random"],
            "Use either --sync-all or --random, not both.",
            id="sync-all-random",
        ),
        pytest.param(
            ["--sync-all", "--no-state"],
            "--sync-all requires a state file (do not use --no-state).",
            id="sync-all-no-state",
        ),
        pytest.param(
            ["--extensions", " , "],
            "No valid extensions provided.",
            id="no-extensions",
        ),
    ],
)
def test_sync_bad_parameter(
    art: Mock, tmp_path: Path, flags: list[str], message: str
) -> None:
    """Conflicting or invalid sync options are rejected."""
    result = invoke("art-sync", str(tmp_path), *flags)

    assert result.exit_code == 2
    assert message in plain_text(result.stderr)
    art.upload.assert_not_called()


def test_sync_folder_not_found(art: Mock, tmp_path: Path) -> None:
    """A missing folder is rejected."""
    missing = tmp_path / "missing"

    result = invoke("art-sync", str(missing))

    assert result.exit_code == 2
    assert "Folder not found" in result.stderr


def test_sync_no_images(art: Mock, tmp_path: Path) -> None:
    """An empty folder exits successfully without touching the TV."""
    write_image(tmp_path / "notes.txt")

    result = invoke("art-sync", str(tmp_path))

    assert result.exit_code == 0
    assert result.output == "OK: no images found\n"
    art.upload.assert_not_called()
    assert not (tmp_path / STATE_FILE_NAME).exists()


@pytest.mark.parametrize(
    ("extra_args", "expected_show"),
    [
        pytest.param([], True, id="default-random"),
        pytest.param(["--random", "--no-show"], False, id="random-no-show"),
    ],
)
def test_sync_random_upload(
    art: Mock, tmp_path: Path, extra_args: list[str], expected_show: bool
) -> None:
    """Random mode uploads the picked image, displays it and saves the state."""
    image = write_image(tmp_path / "a.jpg")
    art.upload.return_value = "MY_F0020"

    result = invoke("art-sync", str(tmp_path), *extra_args)

    assert result.exit_code == 0
    assert result.output.splitlines() == [
        f"OK: uploaded {image} -> MY_F0020",
        "OK: displayed MY_F0020",
        "OK: done (uploaded=1, skipped=0, deleted=0)",
    ]
    art.upload.assert_called_once_with(
        image, matte="shadowbox_polar", portrait_matte="shadowbox_polar"
    )
    art.select_image.assert_called_once_with("MY_F0020", show=expected_show)
    state = json.loads((tmp_path / STATE_FILE_NAME).read_text())
    assert state == {
        "version": 1,
        "files": {image: {"content_id": "MY_F0020", **fingerprint(image)}},
    }


def test_sync_random_cached(art: Mock, tmp_path: Path) -> None:
    """Random mode displays a cached image without uploading it again."""
    image = write_image(tmp_path / "a.jpg")
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"files": {image: {"content_id": "MY_F0021", **fingerprint(image)}}})
    )

    result = invoke("art-sync", str(tmp_path), "--state-file", str(state_file))

    assert result.exit_code == 0
    assert result.output.splitlines() == [
        f"OK: cached {image} -> MY_F0021",
        "OK: displayed MY_F0021",
        "OK: done (uploaded=0, skipped=1, deleted=0)",
    ]
    art.upload.assert_not_called()
    art.select_image.assert_called_once_with("MY_F0021", show=True)


def test_sync_random_refresh(art: Mock, tmp_path: Path) -> None:
    """Random mode with --refresh re-uploads a cached image."""
    image = write_image(tmp_path / "a.jpg")
    (tmp_path / STATE_FILE_NAME).write_text(
        json.dumps({"files": {image: {"content_id": "MY_F0021", **fingerprint(image)}}})
    )
    art.upload.return_value = "MY_F0022"

    result = invoke("art-sync", str(tmp_path), "--refresh", "--file-type", "jpg")

    assert result.exit_code == 0
    art.upload.assert_called_once_with(
        image,
        matte="shadowbox_polar",
        portrait_matte="shadowbox_polar",
        file_type="jpg",
    )
    art.select_image.assert_called_once_with("MY_F0022", show=True)


def test_sync_upload_all(art: Mock, tmp_path: Path) -> None:
    """Upload-all uploads new/changed images and skips cached ones."""
    cached = write_image(tmp_path / "a_cached.jpg")
    size_changed = write_image(tmp_path / "b_size.png")
    mtime_changed = write_image(tmp_path / "c_mtime.jpeg")
    not_dict = write_image(tmp_path / "d_not_dict.jpg")
    bad_id = write_image(tmp_path / "e_bad_id.jpg")
    new = write_image(tmp_path / "sub" / "f_new.JPG")
    write_image(tmp_path / "ignored.gif")
    mtime_fp = fingerprint(mtime_changed)
    (tmp_path / STATE_FILE_NAME).write_text(
        json.dumps(
            {
                "files": {
                    cached: {"content_id": "OLD_A", **fingerprint(cached)},
                    size_changed: {"content_id": "OLD_B", "size": 999, "mtime_ns": 0},
                    mtime_changed: {
                        "content_id": "OLD_C",
                        "size": mtime_fp["size"],
                        "mtime_ns": mtime_fp["mtime_ns"] + 1,
                    },
                    not_dict: "OLD_D",
                    bad_id: {"content_id": 5, **fingerprint(bad_id)},
                }
            }
        )
    )
    art.upload.side_effect = ["NEW_B", "NEW_C", "NEW_D", "NEW_E", "NEW_F"]

    result = invoke("art-sync", str(tmp_path), "--upload-all")

    assert result.exit_code == 0
    assert result.output.splitlines() == [
        f"OK: uploaded {size_changed} -> NEW_B",
        f"OK: uploaded {mtime_changed} -> NEW_C",
        f"OK: uploaded {not_dict} -> NEW_D",
        f"OK: uploaded {bad_id} -> NEW_E",
        f"OK: uploaded {new} -> NEW_F",
        "OK: done (uploaded=5, skipped=1, deleted=0)",
    ]
    art.select_image.assert_not_called()
    state = json.loads((tmp_path / STATE_FILE_NAME).read_text())
    assert {path: entry["content_id"] for path, entry in state["files"].items()} == {
        cached: "OLD_A",
        size_changed: "NEW_B",
        mtime_changed: "NEW_C",
        not_dict: "NEW_D",
        bad_id: "NEW_E",
        new: "NEW_F",
    }


def test_sync_upload_all_refresh(art: Mock, tmp_path: Path) -> None:
    """Upload-all with --refresh re-uploads cached images."""
    image = write_image(tmp_path / "a.jpg")
    (tmp_path / STATE_FILE_NAME).write_text(
        json.dumps({"files": {image: {"content_id": "OLD", **fingerprint(image)}}})
    )
    art.upload.return_value = "NEW"

    result = invoke("art-sync", str(tmp_path), "--upload-all", "--refresh")

    assert result.exit_code == 0
    assert result.output.splitlines() == [
        f"OK: uploaded {image} -> NEW",
        "OK: done (uploaded=1, skipped=0, deleted=0)",
    ]


def test_sync_upload_all_no_recursive(art: Mock, tmp_path: Path) -> None:
    """--no-recursive ignores subfolders."""
    top = write_image(tmp_path / "a.jpg")
    write_image(tmp_path / "sub" / "b.jpg")
    art.upload.return_value = "MY_F0030"

    result = invoke(
        "art-sync",
        str(tmp_path),
        "--upload-all",
        "--no-recursive",
        "--extensions",
        ".JPG",
    )

    assert result.exit_code == 0
    art.upload.assert_called_once_with(
        top, matte="shadowbox_polar", portrait_matte="shadowbox_polar"
    )


def test_sync_no_state(art: Mock, tmp_path: Path) -> None:
    """--no-state neither reads nor writes the state file."""
    image = write_image(tmp_path / "a.jpg")
    (tmp_path / STATE_FILE_NAME).write_text(
        json.dumps({"files": {image: {"content_id": "OLD", **fingerprint(image)}}})
    )
    original_state = (tmp_path / STATE_FILE_NAME).read_text()
    art.upload.return_value = "NEW"

    result = invoke("art-sync", str(tmp_path), "--upload-all", "--no-state")

    assert result.exit_code == 0
    art.upload.assert_called_once()
    assert (tmp_path / STATE_FILE_NAME).read_text() == original_state


@pytest.mark.parametrize(
    "state_content",
    [
        pytest.param("{not json", id="invalid-json"),
        pytest.param('{"files": []}', id="files-not-dict"),
    ],
)
def test_sync_invalid_state_file(art: Mock, tmp_path: Path, state_content: str) -> None:
    """An unreadable state file is treated as empty and rewritten."""
    image = write_image(tmp_path / "a.jpg")
    (tmp_path / STATE_FILE_NAME).write_text(state_content)
    art.upload.return_value = "NEW"

    result = invoke("art-sync", str(tmp_path), "--upload-all")

    assert result.exit_code == 0
    art.upload.assert_called_once()
    state = json.loads((tmp_path / STATE_FILE_NAME).read_text())
    assert state == {
        "version": 1,
        "files": {image: {"content_id": "NEW", **fingerprint(image)}},
    }


def test_sync_all_removes_missing(art: Mock, tmp_path: Path) -> None:
    """Sync-all deletes images missing on disk from the TV and the cache."""
    folder = tmp_path / "images"
    folder.mkdir()
    present = write_image(folder / "present.jpg")
    gone_ok = str(folder / "gone_ok.jpg")
    gone_fail = str(folder / "gone_fail.jpg")
    gone_no_id = str(folder / "gone_no_id.jpg")
    gone_not_dict = str(folder / "gone_not_dict.jpg")
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "files": {
                    present: {"content_id": "KEEP", **fingerprint(present)},
                    gone_ok: {"content_id": "DEL_OK"},
                    gone_fail: {"content_id": "DEL_FAIL"},
                    gone_no_id: {"content_id": None},
                    gone_not_dict: "junk",
                }
            }
        )
    )
    art.delete.side_effect = lambda content_id: content_id == "DEL_OK"

    result = invoke(
        "art-sync", str(folder), "--sync-all", "--state-file", str(state_file)
    )

    assert result.exit_code == 1
    assert result.stdout.splitlines() == [
        f"OK: deleted missing {gone_ok} -> DEL_OK",
        "OK: done (uploaded=0, skipped=1, deleted=1)",
    ]
    assert result.stderr.splitlines() == [
        f"ERROR: failed to delete missing {gone_fail} -> DEL_FAIL",
    ]
    assert [c.args for c in art.delete.call_args_list] == [("DEL_OK",), ("DEL_FAIL",)]
    art.upload.assert_not_called()
    state = json.loads(state_file.read_text())
    assert set(state["files"]) == {present, gone_fail}


def test_sync_all_empty_folder(art: Mock, tmp_path: Path) -> None:
    """Sync-all on an empty folder still removes cached images."""
    gone = str(tmp_path / "gone.jpg")
    (tmp_path / STATE_FILE_NAME).write_text(
        json.dumps({"files": {gone: {"content_id": "DEL"}}})
    )
    art.delete.return_value = True

    result = invoke("art-sync", str(tmp_path), "--sync-all")

    assert result.exit_code == 0
    assert result.output.splitlines() == [
        f"OK: deleted missing {gone} -> DEL",
        "OK: done (uploaded=0, skipped=0, deleted=1)",
    ]
    state = json.loads((tmp_path / STATE_FILE_NAME).read_text())
    assert state == {"version": 1, "files": {}}
