"""Configuration management for the marketplace assistant.

Uses environment variables with pydantic-settings for validation.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    """Application configuration. Immutable after creation."""

    # Telegram / Bot
    bot_token: str = field(default="")
    admin_ids: list[int] = field(default_factory=list)

    # Database
    database_url: str = field(default="sqlite+aiosqlite:///bot.db")
    redis_url: str | None = field(default=None)

    # LLM (GigaChat / OpenAI)
    llm_api_key: str = field(default="")
    llm_model: str = field(default="gpt-4o-mini")
    llm_provider: str = field(default="openai")  # openai | gigachat

    # Marketplace API keys
    wb_api_key: str = field(default="")
    ozon_client_id: str = field(default="")
    ozon_api_key: str = field(default="")

    # Flags
    mock_mode: bool = field(default=True)
    debug: bool = field(default=False)

    # Server
    host: str = field(default="0.0.0.0")
    port: int = field(default=8000)

    @classmethod
    def from_env(cls) -> "Config":
        """Загрузить конфигурацию из переменных окружения."""
        admin_ids_raw = os.getenv("ADMIN_IDS", "")
        admin_ids = [
            int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()
        ]

        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            admin_ids=admin_ids,
            database_url=os.getenv(
                "DATABASE_URL", "sqlite+aiosqlite:///bot.db"
            ),
            redis_url=os.getenv("REDIS_URL") or None,
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            wb_api_key=os.getenv("WB_API_KEY", ""),
            ozon_client_id=os.getenv("OZON_CLIENT_ID", ""),
            ozon_api_key=os.getenv("OZON_API_KEY", ""),
            mock_mode=os.getenv("MOCK_MODE", "true").lower() == "true",
            debug=os.getenv("DEBUG", "false").lower() == "true",
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
        )

    @property
    def is_llm_configured(self) -> bool:
        """LLM настроена? (ключ + не mock_mode)."""
        return bool(self.llm_api_key) and not self.mock_mode

    @property
    def is_wb_configured(self) -> bool:
        return bool(self.wb_api_key) and not self.mock_mode

    @property
    def is_ozon_configured(self) -> bool:
        return bool(self.ozon_client_id) and bool(self.ozon_api_key) and not self.mock_mode
