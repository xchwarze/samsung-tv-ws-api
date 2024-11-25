"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

from .remote import SamsungTVWS
from .shortcuts import SamsungTVShortcuts

__all__ = ["SamsungTVShortcuts", "SamsungTVWS"]
