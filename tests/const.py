"""Constants for tests."""

from pathlib import Path
import re

from typer.testing import CliRunner, Result

from samsungtvws.cli import cli

BASE_ARGS = ["--host", "127.0.0.1", "--token", "abc"]
APP_ID = "111299001912"
ENDPOINT = "samsung.remote.control"
NAME_B64 = "U2Ftc3VuZ1R2UmVtb3Rl"
TOKEN = "037739871315caef138547b03e348b72"
SESSION_ID = "1"
INSTALLED_APPS = [
    {
        "appId": APP_ID,
        "app_type": 2,
        "icon": f"/opt/share/webappservice/apps_icon/FirstScreen/{APP_ID}/250x250.png",
        "is_lock": 0,
        "name": "YouTube",
    },
    {
        "appId": "3201608010191",
        "app_type": 2,
        "icon": "/opt/share/webappservice/apps_icon/FirstScreen/3201608010191/250x250.png",
        "is_lock": 0,
        "name": "Deezer",
    },
]

# CI forces rich terminal output: colored and wrapped in a box
_RICH_MARKUP = re.compile(r"\x1b\[[0-9;]*m|[\u2500-\u257f]")


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    """Return the text of a fixture file."""
    return (FIXTURES_DIR / name).read_text()


def invoke(*args: str) -> Result:
    """Run the CLI with the base connection options."""
    return CliRunner().invoke(cli, [*BASE_ARGS, *args])


def plain_text(text: str) -> str:
    """Return CLI output without rich markup, on a single line."""
    return " ".join(_RICH_MARKUP.sub("", text).split())


D2D_SERVICE_MESSAGE_OK_SAMPLE = _load("event_d2d_service_message_ok_sample.json")
D2D_SERVICE_MESSAGE_AVAILABLE_SAMPLE = _load("event_d2d_service_message_available.json")
D2D_SERVICE_MESSAGE_SEND_IMAGE_ERROR = _load(
    "event_d2d_service_message_send_image_error.json"
)
D2D_SERVICE_MESSAGE_READY_TO_USE_SAMPLE = _load(
    "event_d2d_service_message_ready_to_use.json"
)
D2D_SERVICE_MESSAGE_IMAGE_ADDED_SAMPLE = _load(
    "event_d2d_service_message_image_added.json"
)
D2D_SERVICE_MESSAGE_THUMBNAIL_INLINE_SAMPLE = (
    FIXTURES_DIR / "event_d2d_service_message_thumbnail_inline.bin"
).read_bytes()
MS_CHANNEL_CONNECT_SAMPLE = _load("event_ms_channel_connect.json")
MS_CHANNEL_READY_SAMPLE = _load("event_ms_channel_ready.json")
ED_EDENTV_UPDATE_SAMPLE = _load("event_ed_edentv_update.json")
ED_APPS_LAUNCH_SAMPLE = _load("event_ed_apps_launch.json")
ED_INSTALLED_APP_SAMPLE = _load("event_ed_installedApp_get.json")
MS_ERROR_SAMPLE = _load("event_ms_error.json")
MS_VOICEAPP_HIDE_SAMPLE = _load("event_ms_voiceapp_hide.json")
MS_REMOTE_TOUCH_ENABLE_SAMPLE = _load("event_ms_remote_touch_enable.json")
MS_REMOTE_TOUCH_DISABLE_SAMPLE = _load("event_ms_remote_touch_disable.json")
MS_REMOTE_IME_START_SAMPLE = _load("event_ms_remote_ime_start.json")
MS_REMOTE_IME_END_SAMPLE = _load("event_ms_remote_ime_end.json")
REST_DEVICE_INFO_SAMPLE = _load("rest_device_info.json")
REST_APP_STATUS_SAMPLE = _load("rest_app_status.json")
MS_CHANNEL_CONNECT_TOKEN_SAMPLE = _load("event_ms_channel_connect_token.json")
MS_CHANNEL_UNAUTHORIZED_SAMPLE = _load("event_ms_channel_unauthorized.json")
MS_ERROR_REMOTE_CONTROL_SAMPLE = _load("event_ms_error_remote_control.json")
AUTH_PIN_STATUS_SAMPLE = _load("auth_pin_status.xml")
AUTH_EMPTY_SAMPLE = _load("auth_empty.json")
AUTH_GENERATOR_CLIENT_HELLO_SAMPLE = _load("auth_generator_client_hello.json")
AUTH_CLIENT_ACK_MSG_SAMPLE = _load("auth_client_ack_msg.json")
