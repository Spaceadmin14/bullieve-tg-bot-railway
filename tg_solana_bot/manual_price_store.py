import json
import os
from typing import Dict, Optional


class ManualPriceStore:
    def __init__(self, file_path: str) -> None:
        self._file_path = file_path
        self._prices: Dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(self._file_path):
                with open(self._file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Normalize keys to upper-case symbols and known mints
                self._prices = {str(k).upper(): float(v) for k, v in data.items() if isinstance(v, (int, float))}
        except Exception:
            self._prices = {}

    def refresh(self) -> None:
        self._load()

    def get_price_usd(self, symbol_or_mint: str) -> Optional[float]:
        # Support both symbols (SOL/USDC/USDT/...) and full mint strings.
        key = symbol_or_mint.upper()
        if key in self._prices:
            return self._prices[key]
        # Try mapping WSOL mint to SOL
        if symbol_or_mint == "So11111111111111111111111111111111111111112":
            return self._prices.get("SOL")
        return self._prices.get(symbol_or_mint)


