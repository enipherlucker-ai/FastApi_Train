import logging

from bot.qr import is_receipt, read_qr_codes
from bot.receipt_api import ReceiptApi, ReceiptApiError, ReceiptDuplicateError
from bot.telegram_api import TelegramAPI

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Пришли фото QR-кода с чека, и я добавлю чек в базу.\n"
    "Если фото не читается, пришли картинку файлом (без сжатия) "
    "или текст из QR-кода: t=...&s=...&fn=...&i=...&fp=...&n=..."
)


def get_image_file_id(message: dict) -> str | None:
    if "photo" in message:
        return message["photo"][-1]["file_id"]
    document = message.get("document")
    if document and document.get("mime_type", "").startswith("image/"):
        return document["file_id"]
    return None


async def find_raw_receipt(message: dict, tg: TelegramAPI) -> str | None:
    text = message.get("text")
    if text and is_receipt(text):
        return text.strip()

    file_id = get_image_file_id(message)
    if file_id is None:
        return None
    image_bytes = await tg.download_file(file_id)
    for code in read_qr_codes(image_bytes):
        if is_receipt(code):
            return code
    return None

async def handle_message(message: dict, tg: TelegramAPI, api: ReceiptApi, allowed_user_ids: list[int]) -> None:
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    user_id = message.get("from", {}).get("id")

    if user_id not in allowed_user_ids:
        await tg.send_message(chat_id, "Нет доступа к боту")
        return

    await tg.send_chat_action(chat_id)
    raw_receipt = await find_raw_receipt(message, tg)
    if raw_receipt is None:
        await tg.send_message(chat_id, "Не найден QR-код чека " + HELP_TEXT, reply_to=message_id)
        return

    try:
        receipt_id = await api.create_receipt(raw_receipt)
    except ReceiptDuplicateError:
        await tg.send_message(chat_id, "Этот чек уже есть в базе", reply_to=message_id)
        return
    except ReceiptApiError as exc:
        logger.warning("Чек не добавлен: %s", exc)
        await tg.send_message(chat_id, f"Не удалось добавить чек {exc}", reply_to=message_id)
        return

    await tg.send_message(chat_id, f"Чек сохранён, id: {receipt_id}", reply_to=message_id)

