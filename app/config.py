from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseModel):
    host: str
    port: int = 5432
    user: str
    password: str = Field(default="", repr=False)
    database: str
    echo: bool = False

    @property
    def url(self):
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

class CheckReceiptSettings(BaseModel):
    token: str = Field(default="", repr=False)
    url: str
    timeout: int = 30

class OpenAISettings(BaseModel):
    api_key: str = Field(default="", repr=False)
    model: str = "gpt-5.4-mini"
    base_url: str | None = None
    timeout: int = 30

class Settings(BaseSettings):
    app_env: str = "dev"
    postgres_settings: PostgresSettings
    check_receipt_settings: CheckReceiptSettings
    open_ai_settings:OpenAISettings = OpenAISettings()


    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
