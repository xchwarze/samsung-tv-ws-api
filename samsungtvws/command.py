import json
from typing import Any, Dict


class SamsungTVCommand:
    def __init__(self, method: str, params: Any) -> None:
        self.method = method
        self.params = params

    def as_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "params": self.params,
        }

    def get_payload(self) -> str:
        return json.dumps(self.as_dict())
