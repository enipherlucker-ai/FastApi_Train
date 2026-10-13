import httpx

class BadRequestError(httpx.HTTPStatusError):
    """400 — некорректный запрос."""


class UnauthorizedError(httpx.HTTPStatusError):
    """401 — требуется аутентификация."""


class ForbiddenError(httpx.HTTPStatusError):
    """403 — доступ запрещён."""


class NotFoundError(httpx.HTTPStatusError):
    """404 — ресурс не найден."""


class ConflictError(httpx.HTTPStatusError):
    """409 — конфликт с текущим состоянием ресурса."""


class UnprocessableEntityError(httpx.HTTPStatusError):
    """422 — сервер не может обработать содержимое запроса."""


class TooManyRequestsError(httpx.HTTPStatusError):
    """429 — превышен лимит запросов."""


class InternalServerError(httpx.HTTPStatusError):
    """500 — внутренняя ошибка сервера."""


class BadGatewayError(httpx.HTTPStatusError):
    """502 — шлюз получил некорректный ответ upstream-сервера."""


class ServiceUnavailableError(httpx.HTTPStatusError):
    """503 — сервис недоступен."""


class GatewayTimeoutError(httpx.HTTPStatusError):
    """504 — шлюз не дождался ответа upstream-сервера."""


STATUS_ERRORS: dict[int, type[httpx.HTTPStatusError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: TooManyRequestsError,
    500: InternalServerError,
    502: BadGatewayError,
    503: ServiceUnavailableError,
    504: GatewayTimeoutError,
}