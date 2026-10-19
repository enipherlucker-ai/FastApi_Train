from typing import Any

import httpx


class TelegramError(Exception):
    """Telegram не ответил или ответил ok=false"""


class TelegramAPI:
    def __init__(self, token: str, base_url: str, client: httpx.AsyncClient) -> None:
        self.token = token
        self.base_url = base_url
        self.client = client

    async def call(self, method: str, params: dict | None = None, http_timeout: float = 10) -> Any:
        url = f'{self.base_url}/bot{self.token}/{method}'
        try:
            response = await self.client.post(url, json=params or {}, timeout=http_timeout)
            data = response.json()
        except httpx.HTTPError as e:
            raise TelegramError(f"{method}: нет связи с Telegram API ({type(e).__name__})") from None
        except ValueError:
            raise TelegramError(f"{method}: Telegram API вернул не JSON, HTTP ({response.status_code})") from None

        if not data.get("ok"):
            raise TelegramError(f"{method}: {data.get('error_code')} {data.get('description')}")
        return data["result"]

    async def get_update(self, offset: int, timeout: int) -> list[dict]:
        params = {"offset": offset, "timeout": timeout, "allowed_updates": ["message"]}
        return await self.call("getUpdates", params=params, http_timeout=timeout + 10)

    async def send_message(self, chat_id: int, text: str, reply_to: int | None = None) -> dict:
        params = {"chat_id": chat_id, "text": text}
        if reply_to is not None:
            params["reply_parameters"] = {"message_id": reply_to}
        return await self.call("sendMessage", params=params)

    async def send_chat_action(self, chat_id: int, action: str = "typing") -> None:
        await self.call("sendChatAction", {"chat_id": chat_id, "action": action})

    async def download_file(self, file_id: str) -> bytes:
        file = await self.call("getFile", {"file_id": file_id})
        url = f"{self.base_url}/file/bot{self.token}/{file['file_path']}"
        try:
            response = await self.client.get(url, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TelegramError(f"Не удалось скачать файл ({type(exc).__name__})") from None
        return response.content
