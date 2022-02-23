from __future__ import annotations

import json
from typing import Any


class SamsungTVCommand:
    def __init__(self, method: str, params: Any) -> None:
        self.method = method
        self.params = params

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "params": self.params,
        }

    def get_payload(self) -> str:
        return json.dumps(self.as_dict())
