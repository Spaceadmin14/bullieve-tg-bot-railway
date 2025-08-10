from typing import Optional
import aiohttp


_STABLE_MINTS = {
    # USDC
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 1.0,
    # USDT
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 1.0,
}


class PriceClient:
    def __init__(self, manual_store=None) -> None:
        self._session: Optional[aiohttp.ClientSession] = None
        self._manual_store = manual_store

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=20)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_usd_price(self, mint_or_symbol: str) -> Optional[float]:
        # Stablecoins shortcut
        if mint_or_symbol in _STABLE_MINTS:
            return _STABLE_MINTS[mint_or_symbol]

        # Map wSOL mint to symbol SOL
        if mint_or_symbol == "So11111111111111111111111111111111111111112":
            ids = "SOL"
        elif mint_or_symbol.upper() == "SOL":
            ids = "SOL"
        else:
            ids = mint_or_symbol

        # 1) Jupiter price API first
        url = f"https://price.jup.ag/v6/price?ids={ids}"
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception("jup price http status")
                data = await resp.json()
                price_obj = (data.get("data", {}) or {}).get(ids)
                if not price_obj:
                    raise Exception("jup price empty")
                price = price_obj.get("price")
                try:
                    return float(price)
                except Exception:
                    raise
        except Exception:
            # 2) Manual store fallback
            if self._manual_store is not None:
                mp = self._manual_store.get_price_usd(mint_or_symbol)
                if mp is not None:
                    return mp
            # 3) No price available
            return None


