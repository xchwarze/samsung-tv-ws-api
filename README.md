<p align="center">
    <img src="https://user-images.githubusercontent.com/5860071/47255992-611d9b00-d481-11e8-965d-d9816f254be2.png" width="300px" border="0" />
    <br/>
    <a href="https://github.com/xchwarze/samsung-tv-ws-api/releases/latest">
        <img src="https://img.shields.io/badge/version-1.6.0-brightgreen.svg?style=flat-square" alt="Version">
    </a>
    Samsung Smart TV WS API wrapper
</p>

This project is a library for remote controlling Samsung televisions via a TCP/IP connection.

It currently supports modern (post-2016) TVs with Ethernet or Wi-Fi connectivity. They should be all models with TizenOs.

Based on https://github.com/marysieek/samsung-tv-api work

## Install

```bash
$ pip3 install samsungtvws
```
or
```bash
$ pip3 install git+https://github.com/xchwarze/samsung-tv-ws-api.git
```
or...!
```bash
$ git clone https://github.com/xchwarze/samsung-tv-ws-api
$ pip3 install ./samsung-tv-ws-api
```

## Usage

```python
import sys
import os
import logging
import wakeonlan

sys.path.append('../')

from samsungtvws import SamsungTVWS

# Increase debug level
logging.basicConfig(level=logging.INFO)

# Normal constructor
tv = SamsungTVWS('192.168.xxx.xxx')

# Autosave token to file 
token_file = os.path.dirname(os.path.realpath(__file__)) + '/tv-token.txt'
tv = SamsungTVWS(host='192.168.xxx.xxx', port=8002, token_file=token_file)

# Toggle power
tv.shortcuts().power()

# Power On
wakeonlan.send_magic_packet('CC:6E:A4:xx:xx:xx')

# Open web in browser
tv.open_browser('https://duckduckgo.com/')

# View installed apps
apps = tv.app_list()
logging.info(apps)

# Open app (Spotify)
tv.run_app('3201606009684')

# Get app status (Spotify)
app = tv.rest_app_status('3201606009684')
logging.info(app)

# Open app (Spotify)
app = tv.rest_app_run('3201606009684')
logging.info(app)

# Close app (Spotify)
app = tv.rest_app_close('3201606009684')
logging.info(app)

# Install from official store (Spotify)
app = tv.rest_app_install('3201606009684')
logging.info(app)

# Get device info (device name, model, supported features..)
info = tv.rest_device_info()
logging.info(info)

```

## Art Mode

TVs that support art mode (such as The Frame) can be controlled as follows:

```
from samsungtvws import SamsungTVWS
tv = SamsungTVWS('192.168.xxx.xxx')

# Is art mode supported?
print (tv.art().supported())

# List the art available on the device
print(tv.art().available())

# Retrieve information about the currently selected art
print(tv.art().get_current())

# Retrieve a thumbnail for a specific piece of art. Returns a JPEG.
thumbnail = tv.art().get_thumbnail('SAM-F0206')

# Set a piece of art
tv.art().set('SAM-F0206')

# Set a piece of art, but don't immediately show it if not in art mode
tv.art().set('SAM-F0201', show=False)

# Determine whether the TV is currently in art mode
print(tv.art().get_artmode())

# Switch art mode on or off
tv.art().set_artmode(True)
tv.art().set_artmode(False)

# Upload a picture
file = open("test.png", "rb")
data = file.read()
tv.art().upload(data)

# If uploading a JPEG
tv.art().upload(data, filetype='JPEG')

# To set the matte to modern and apricot color
tv.art().upload(data, matte='modern_apricot')

# Delete an uploaded item
tv.art().delete("MY-F0020")

# Delete multiple uploaded items
tv.art().delete_list(["MY-F0020", "MY-F0021"])

# List available photo filters
print(tv.art().get_photo_filter_list())

# Apply a filter to a specific piece of art
tv.art().set_photo_filter('SAM-F0206', 'ink')
```

## Supported TVs

List of support TV models. https://developer.samsung.com/smarttv/develop/extension-libraries/smart-view-sdk/supported-device/supported-tvs.html

```
2017 : M5500 and above
2016 : K4300, K5300 and above
2015 : J5500 and above (except J6203)
2014 : H4500, H5500 and above (except H6003/H6103/H6153/H6201/H6203)
Supported TV models may vary by region.
```

For complete list https://developer.samsung.com/smarttv/develop/specifications/tv-model-groups.html

## License

MIT
