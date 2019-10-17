<p align="center">
    <img src="https://user-images.githubusercontent.com/5860071/47255992-611d9b00-d481-11e8-965d-d9816f254be2.png" width="300px" border="0" />
    <br/>
    <a href="https://github.com/xchwarze/samsung-tv-ws-api/releases/latest">
        <img src="https://img.shields.io/badge/version-1.0.0-brightgreen.svg?style=flat-square" alt="Version">
    </a>
    Samsung Smart TV WS API wrapper
</p>

This project is a library for remote controlling Samsung televisions via a TCP/IP connection. 
It currently supports modern (post-2016) TVs with Ethernet or Wi-Fi connectivity.

Based on https://github.com/marysieek/samsung-tv-api work

## Install

```bash
$ pip3 install git+https://github.com/xchwarze/samsung-tv-ws-api.git
```
or
```bash
$ git clone https://github.com/xchwarze/samsung-tv-ws-api
$ pip3 install ./samsung-tv-ws-api
```

## Usage

```python
import sys
import os
import wakeonlan

sys.path.append('../')

from samsungtvws import SamsungTVWS

# Toggle power
tv = SamsungTVWS('192.168.xxx.xxx')
tv.power()

# Power On
wakeonlan.send_magic_packet('CC:6E:A4:xx:xx:xx')

# Autosave token to file
token_file = os.path.dirname(os.path.realpath(__file__)) + '/tv-token.txt'
tv = SamsungTVWS(host='192.168.xxx.xxx', token_file=token_file)
tv.power()

# Open web in browser
tv = SamsungTVWS('192.168.xxx.xxx')
tv.open_browser('https://duckduckgo.com/')

# Open Spotify
# https://github.com/Ape/samsungctl/issues/75
tv = SamsungTVWS('192.168.xxx.xxx')
tv.run_app('rJeHak5zRg.Spotify')

```

## License

MIT
