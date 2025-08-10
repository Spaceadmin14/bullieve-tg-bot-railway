from typing import Optional, List
import aiohttp
import asyncio
import os


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, chat_ids: Optional[List[str]] = None) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._chat_ids = chat_ids or ([chat_id] if chat_id else [])
        self._base = f"https://api.telegram.org/bot{bot_token}"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_text(self, text: str, disable_web_page_preview: bool = True) -> None:
        session = await self._get_session()
        url = f"{self._base}/sendMessage"
        for cid in self._chat_ids:
            payload = {
                "chat_id": cid,
                "text": text,
                "disable_web_page_preview": disable_web_page_preview,
                "parse_mode": "HTML",
            }
            async with session.post(url, json=payload) as resp:
                await resp.text()

    async def send_media(self, media_url: str, caption: str = "", media_type: str = "photo") -> None:
        if not media_url:
            await self.send_text(caption)
            return
        session = await self._get_session()
        for cid in self._chat_ids:
            endpoint = "sendPhoto" if media_type == "photo" else (
                "sendAnimation" if media_type == "animation" else "sendVideo"
            )
            url = f"{self._base}/{endpoint}"
            # If media_url points to a local file path, upload the file; otherwise pass the URL
            if os.path.isfile(media_url):
                form = aiohttp.FormData()
                form.add_field("chat_id", str(cid))
                field_name = "photo" if media_type == "photo" else ("animation" if media_type == "animation" else "video")
                with open(media_url, "rb") as f:
                    form.add_field(field_name, f, filename=os.path.basename(media_url), content_type="application/octet-stream")
                    if caption:
                        form.add_field("caption", caption)
                    async with session.post(url, data=form) as resp:
                        await resp.text()
            else:
                # Assume it's a URL
                if media_type == "photo":
                    payload = {"chat_id": cid, "photo": media_url, "caption": caption}
                elif media_type == "animation":
                    payload = {"chat_id": cid, "animation": media_url, "caption": caption}
                else:
                    payload = {"chat_id": cid, "video": media_url, "caption": caption}
                async with session.post(url, data=payload) as resp:
                    await resp.text()


