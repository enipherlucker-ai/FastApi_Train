from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class TelegramSettings(BaseModel):
    token: str = Field(repr=False)
    base_url: str = "https://api.telegram.org"
    allowed_user_ids: list[int] = []
    poll_timeout: int = 30
    proxy: str | None = None


class ReceiptApiSettings(BaseModel):
    url: str = "http://127.0.0.1:8000"
    timeout: int = 90


class BotSettings(BaseSettings):
    telegram_settings: TelegramSettings
    receipt_api_settings: ReceiptApiSettings = ReceiptApiSettings()

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()