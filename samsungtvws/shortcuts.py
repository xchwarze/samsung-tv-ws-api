"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""


class SamsungTVShortcuts:
    def __init__(self, remote):
        self.remote = remote

    # power
    def power(self):
        self.remote.send_key("KEY_POWER")

    # menu
    def home(self):
        self.remote.send_key("KEY_HOME")

    def menu(self):
        self.remote.send_key("KEY_MENU")

    def source(self):
        self.remote.send_key("KEY_SOURCE")

    def guide(self):
        self.remote.send_key("KEY_GUIDE")

    def tools(self):
        self.remote.send_key("KEY_TOOLS")

    def info(self):
        self.remote.send_key("KEY_INFO")

    # navigation
    def up(self):
        self.remote.send_key("KEY_UP")

    def down(self):
        self.remote.send_key("KEY_DOWN")

    def left(self):
        self.remote.send_key("KEY_LEFT")

    def right(self):
        self.remote.send_key("KEY_RIGHT")

    def enter(self, count=1):
        self.remote.send_key("KEY_ENTER")

    def back(self):
        self.remote.send_key("KEY_RETURN")

    # channel
    def channel_list(self):
        self.remote.send_key("KEY_CH_LIST")

    def channel(self, ch):
        for c in str(ch):
            self.digit(c)

        self.enter()

    def digit(self, d):
        self.remote.send_key("KEY_" + d)

    def channel_up(self):
        self.remote.send_key("KEY_CHUP")

    def channel_down(self):
        self.remote.send_key("KEY_CHDOWN")

    # volume
    def volume_up(self):
        self.remote.send_key("KEY_VOLUP")

    def volume_down(self):
        self.remote.send_key("KEY_VOLDOWN")

    def mute(self):
        self.remote.send_key("KEY_MUTE")

    # extra
    def red(self):
        self.remote.send_key("KEY_RED")

    def green(self):
        self.remote.send_key("KEY_GREEN")

    def yellow(self):
        self.remote.send_key("KEY_YELLOW")

    def blue(self):
        self.remote.send_key("KEY_BLUE")
