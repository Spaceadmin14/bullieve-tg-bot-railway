from typing import Any, Dict, List, Optional
import aiohttp
import asyncio


class SolanaClient:
    def __init__(self, rpc_url: str, alt_rpc_url: str = "") -> None:
        self._rpc_url = rpc_url
        self._alt_rpc_url = alt_rpc_url.strip()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_token_accounts_by_owner(self, owner: str) -> List[str]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                owner,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"},
            ],
        }
        session = await self._get_session()
        for attempt in range(4):
            try:
                async with session.post(
                    self._rpc_url,
                    json=payload,
                    timeout=30,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    if resp.status == 429:
                        backoff = 1.5 ** attempt
                        await asyncio.sleep(backoff)
                        if self._alt_rpc_url:
                            self._rpc_url, self._alt_rpc_url = self._alt_rpc_url, self._rpc_url
                        continue
                    resp.raise_for_status()
                    data = await resp.json()
                    result = data.get("result", {})
                    value = result.get("value", []) if isinstance(result, dict) else []
                    addrs: List[str] = []
                    for entry in value:
                        pubkey = entry.get("pubkey") if isinstance(entry, dict) else None
                        if pubkey:
                            addrs.append(pubkey)
                    return addrs
            except aiohttp.ClientError:
                backoff = 1.5 ** attempt
                await asyncio.sleep(backoff)
                continue
        return []

    async def get_signatures_for_address(
        self,
        address: str,
        before: Optional[str] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                address,
                {"before": before, "limit": limit} if before else {"limit": limit},
            ],
        }
        session = await self._get_session()
        for attempt in range(4):
            try:
                url = self._rpc_url
                async with session.post(
                    url,
                    json=payload,
                    timeout=30,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    if resp.status == 429:
                        backoff = 1.5 ** attempt
                        await asyncio.sleep(backoff)
                        # try alternate RPC if provided
                        if self._alt_rpc_url:
                            self._rpc_url, self._alt_rpc_url = self._alt_rpc_url, self._rpc_url
                        continue
                    resp.raise_for_status()
                    data = await resp.json()
                    return data.get("result", [])
            except aiohttp.ClientError:
                backoff = 1.5 ** attempt
                await asyncio.sleep(backoff)
                continue
        return []

    async def get_transaction(self, signature: str) -> Optional[Dict[str, Any]]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        }
        session = await self._get_session()
        for attempt in range(4):
            try:
                url = self._rpc_url
                async with session.post(
                    url,
                    json=payload,
                    timeout=30,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    if resp.status == 429:
                        backoff = 1.5 ** attempt
                        await asyncio.sleep(backoff)
                        if self._alt_rpc_url:
                            self._rpc_url, self._alt_rpc_url = self._alt_rpc_url, self._rpc_url
                        continue
                    resp.raise_for_status()
                    data = await resp.json()
                    return data.get("result")
            except aiohttp.ClientError:
                backoff = 1.5 ** attempt
                await asyncio.sleep(backoff)
                continue
        return None

    @staticmethod
    def get_first_signer_address(tx: Dict[str, Any]) -> Optional[str]:
        try:
            message = (tx.get("transaction") or {}).get("message") or {}
            acct_keys = message.get("accountKeys", []) or []
            for k in acct_keys:
                if isinstance(k, dict):
                    if k.get("signer"):
                        return k.get("pubkey")
                else:
                    # older format: first key is signer
                    return str(k)
        except Exception:
            return None
        return None


