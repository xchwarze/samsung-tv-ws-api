"""Constants for tests."""

with open("tests/fixtures/event_ms_channel_connect.json") as file:
    MS_CHANNEL_CONNECT_SAMPLE = file.read()
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
