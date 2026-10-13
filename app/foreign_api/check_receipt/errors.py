class CheckReceiptError(Exception):
    """Базовая ошибка сервиса проверки чеков."""


class CheckReceiptUnavailableError(CheckReceiptError):
    """Сервис не ответил: таймаут, нет сети или ответ 4xx/5xx."""


class ReceiptNotFoundError(CheckReceiptError):
    """Сервис ответил, но чек проверить не смог (code != 1)."""
