"""Constants for tests."""

import re

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


def plain_text(text: str) -> str:
    """Return CLI output without rich markup, on a single line."""
    return " ".join(_RICH_MARKUP.sub("", text).split())


with open("tests/fixtures/event_d2d_service_message_ok_sample.json") as file:
    D2D_SERVICE_MESSAGE_OK_SAMPLE = file.read()
with open("tests/fixtures/event_d2d_service_message_available.json") as file:
    D2D_SERVICE_MESSAGE_AVAILABLE_SAMPLE = file.read()
with open("tests/fixtures/event_d2d_service_message_send_image_error.json") as file:
    D2D_SERVICE_MESSAGE_SEND_IMAGE_ERROR = file.read()
with open("tests/fixtures/event_d2d_service_message_ready_to_use.json") as file:
    D2D_SERVICE_MESSAGE_READY_TO_USE_SAMPLE = file.read()
with open("tests/fixtures/event_d2d_service_message_image_added.json") as file:
    D2D_SERVICE_MESSAGE_IMAGE_ADDED_SAMPLE = file.read()
with open(
    "tests/fixtures/event_d2d_service_message_thumbnail_inline.bin", "rb"
) as file:
    D2D_SERVICE_MESSAGE_THUMBNAIL_INLINE_SAMPLE = file.read()
with open("tests/fixtures/event_ms_channel_connect.json") as file:
    MS_CHANNEL_CONNECT_SAMPLE = file.read()
with open("tests/fixtures/event_ms_channel_ready.json") as file:
    MS_CHANNEL_READY_SAMPLE = file.read()
with open("tests/fixtures/event_ed_edentv_update.json") as file:
    ED_EDENTV_UPDATE_SAMPLE = file.read()
with open("tests/fixtures/event_ed_apps_launch.json") as file:
    ED_APPS_LAUNCH_SAMPLE = file.read()
with open("tests/fixtures/event_ed_installedApp_get.json") as file:
    ED_INSTALLED_APP_SAMPLE = file.read()
with open("tests/fixtures/event_ms_error.json") as file:
    MS_ERROR_SAMPLE = file.read()
with open("tests/fixtures/event_ms_voiceapp_hide.json") as file:
    MS_VOICEAPP_HIDE_SAMPLE = file.read()
with open("tests/fixtures/event_ms_remote_touch_enable.json") as file:
    MS_REMOTE_TOUCH_ENABLE_SAMPLE = file.read()
with open("tests/fixtures/event_ms_remote_touch_disable.json") as file:
    MS_REMOTE_TOUCH_DISABLE_SAMPLE = file.read()
with open("tests/fixtures/event_ms_remote_ime_start.json") as file:
    MS_REMOTE_IME_START_SAMPLE = file.read()
with open("tests/fixtures/event_ms_remote_ime_end.json") as file:
    MS_REMOTE_IME_END_SAMPLE = file.read()
with open("tests/fixtures/rest_device_info.json") as file:
    REST_DEVICE_INFO_SAMPLE = file.read()
with open("tests/fixtures/rest_app_status.json") as file:
    REST_APP_STATUS_SAMPLE = file.read()
with open("tests/fixtures/event_ms_channel_connect_token.json") as file:
    MS_CHANNEL_CONNECT_TOKEN_SAMPLE = file.read()
with open("tests/fixtures/event_ms_channel_unauthorized.json") as file:
    MS_CHANNEL_UNAUTHORIZED_SAMPLE = file.read()
with open("tests/fixtures/event_ms_error_remote_control.json") as file:
    MS_ERROR_REMOTE_CONTROL_SAMPLE = file.read()
with open("tests/fixtures/auth_pin_status.xml") as file:
    AUTH_PIN_STATUS_SAMPLE = file.read()
with open("tests/fixtures/auth_empty.json") as file:
    AUTH_EMPTY_SAMPLE = file.read()
with open("tests/fixtures/auth_generator_client_hello.json") as file:
    AUTH_GENERATOR_CLIENT_HELLO_SAMPLE = file.read()
with open("tests/fixtures/auth_client_ack_msg.json") as file:
    AUTH_CLIENT_ACK_MSG_SAMPLE = file.read()
