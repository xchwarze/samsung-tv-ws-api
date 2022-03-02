import logging
import os
import sys

import wakeonlan

sys.path.append("../")

from samsungtvws import SamsungTVWS  # noqa: E402

# Increase debug level
logging.basicConfig(level=logging.INFO)

# Normal constructor
tv = SamsungTVWS("192.168.xxx.xxx")

# Autosave token to file
token_file = os.path.dirname(os.path.realpath(__file__)) + "/tv-token.txt"
tv = SamsungTVWS(host="192.168.xxx.xxx", port=8002, token_file=token_file)

# Toggle power
tv.shortcuts().power()

# Power On
wakeonlan.send_magic_packet("CC:6E:A4:xx:xx:xx")

# Open web in browser
tv.open_browser("https://duckduckgo.com/")

# View installed apps
apps = tv.app_list()
logging.info(apps)

# Open app (Spotify)
tv.run_app("3201606009684")

# Get app status (Spotify)
app = tv.rest_app_status("3201606009684")
logging.info(app)

# Open app (Spotify)
app = tv.rest_app_run("3201606009684")
logging.info(app)

# Close app (Spotify)
app = tv.rest_app_close("3201606009684")
logging.info(app)

# Install from official store (Spotify)
app = tv.rest_app_install("3201606009684")
logging.info(app)

# Get device info (device name, model, supported features..)
info = tv.rest_device_info()
logging.info(info)
