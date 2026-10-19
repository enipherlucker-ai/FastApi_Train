import asyncio
import logging

import httpx

from bot.config import get_settings
from bot.handlers import handle_message
from bot.receipt_api import ReceiptApi
from bot.telegram_api import TelegramAPI, TelegramError

logger = logging.getLogger("bot")


async def run() -> None:
    settings = get_settings()
    async with (
        httpx.AsyncClient(proxy=settings.telegram_settings.proxy or None) as tg_client,
        httpx.AsyncClient(trust_env=False) as api_client,
    ):
        tg = TelegramAPI(
            token=settings.telegram_settings.token,
            base_url=settings.telegram_settings.base_url,
            client=tg_client
        )
        api = ReceiptApi(
            url=settings.receipt_api_settings.url,
            timeout=settings.receipt_api_settings.timeout,
            client=api_client
        )

        me = await tg.call("getMe")
        logger.info("Бот @%s запущен, API: %s", me["username"], settings.receipt_api_settings.url)

        offset = 0
        while True:
            try:
                updates = await tg.get_update(offset=offset, timeout=settings.telegram_settings.poll_timeout)
            except TelegramError as exc:
                logger.warning("%s. Повтор через 5 секунд", exc)
                await asyncio.sleep(5)
                continue

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message")
                if message is None:
                    continue
                try:
                    await handle_message(message, tg, api, settings.telegram_settings.allowed_user_ids)
                except Exception:
                    logger.exception("Не обработан update %s", update["update_id"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    main()