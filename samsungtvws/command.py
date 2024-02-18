"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 DSR! <xchwarze@gmail.com>

SPDX-License-Identifier: LGPL-3.0
"""

import json
from typing import Any, Dict


class SamsungTVCommand:
    def __init__(self, method: str, params: Dict[str, Any]) -> None:
        self.method = method
        self.params = params

    def as_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "params": self.params,
        }

    def get_payload(self) -> str:
        return json.dumps(self.as_dict())


class SamsungTVSleepCommand(SamsungTVCommand):
    def __init__(self, delay: float) -> None:
        super().__init__("sleep", {})
        self.delay = delay

    def as_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("Cannot use as_dict on SamsungTVSleepCommand")

    def get_payload(self) -> str:
        raise NotImplementedError("Cannot use get_payload on SamsungTVSleepCommand")
