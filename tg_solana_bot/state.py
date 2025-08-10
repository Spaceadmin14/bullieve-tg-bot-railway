import json
import os
from typing import Optional


class StateStore:
    def __init__(self, path: str) -> None:
        self._path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def load_last_signature(self, wallet_key: str) -> Optional[str]:
        if not os.path.exists(self._path):
            return None
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("last_signature", {}).get(wallet_key)

    def save_last_signature(self, wallet_key: str, signature: str) -> None:
        data = {"last_signature": {}}
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = {"last_signature": {}}
        data.setdefault("last_signature", {})[wallet_key] = signature
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


