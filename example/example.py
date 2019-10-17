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
