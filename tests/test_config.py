"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from config import Config


class TestConfig:
    """Тесты конфигурации."""

    def test_config_defaults(self):
        """Проверка значений по умолчанию."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_env()
            assert config.bot_token == ""
            assert config.admin_ids == []
            assert config.database_url == "sqlite+aiosqlite:///bot.db"
            assert config.redis_url is None
            assert config.llm_api_key == ""
            assert config.llm_model == "gpt-4o-mini"
            assert config.llm_provider == "openai"
            assert config.wb_api_key == ""
            assert config.ozon_client_id == ""
            assert config.ozon_api_key == ""
            assert config.mock_mode is True
            assert config.debug is False
            assert config.host == "0.0.0.0"
            assert config.port == 8000

    def test_config_from_env(self):
        """Проверка загрузки конфигурации из переменных окружения."""
        env_vars = {
            "BOT_TOKEN": "test-bot-token",
            "ADMIN_IDS": "123,456,789",
            "DATABASE_URL": "postgresql://localhost/db",
            "REDIS_URL": "redis://localhost:6379/0",
            "LLM_API_KEY": "llm-key",
            "LLM_MODEL": "gpt-4",
            "LLM_PROVIDER": "gigachat",
            "WB_API_KEY": "wb-key",
            "OZON_CLIENT_ID": "ozon-client",
            "OZON_API_KEY": "ozon-key",
            "MOCK_MODE": "false",
            "DEBUG": "true",
            "HOST": "127.0.0.1",
            "PORT": "9000",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.bot_token == "test-bot-token"
            assert config.admin_ids == [123, 456, 789]
            assert config.database_url == "postgresql://localhost/db"
            assert config.redis_url == "redis://localhost:6379/0"
            assert config.llm_api_key == "llm-key"
            assert config.llm_model == "gpt-4"
            assert config.llm_provider == "gigachat"
            assert config.wb_api_key == "wb-key"
            assert config.ozon_client_id == "ozon-client"
            assert config.ozon_api_key == "ozon-key"
            assert config.mock_mode is False
            assert config.debug is True
            assert config.host == "127.0.0.1"
            assert config.port == 9000

    def test_config_properties(self):
        """Проверка свойств конфигурации."""
        # mock_mode=True => не настроено
        with patch.dict(os.environ, {
            "MOCK_MODE": "true",
            "LLM_API_KEY": "",
            "WB_API_KEY": "",
        }, clear=True):
            config = Config.from_env()
            assert config.is_llm_configured is False
            assert config.is_wb_configured is False
            assert config.is_ozon_configured is False

        # mock_mode=False + ключи => настроено
        with patch.dict(os.environ, {
            "MOCK_MODE": "false",
            "LLM_API_KEY": "key123",
            "LLM_PROVIDER": "openai",
            "WB_API_KEY": "wb-key",
            "OZON_CLIENT_ID": "oz-client",
            "OZON_API_KEY": "oz-key",
        }, clear=True):
            config = Config.from_env()
            assert config.is_llm_configured is True
            assert config.is_wb_configured is True
            assert config.is_ozon_configured is True

    def test_config_frozen(self):
        """Проверка, что конфиг не изменяем (dataclass frozen)."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_env()
            with pytest.raises(Exception):
                config.bot_token = "new-token"  # frozen dataclass

    def test_config_admin_ids_empty(self):
        """Проверка обработки пустого ADMIN_IDS."""
        with patch.dict(os.environ, {"ADMIN_IDS": ""}, clear=True):
            config = Config.from_env()
            assert config.admin_ids == []

    def test_config_admin_ids_single(self):
        """Проверка обработки одного ADMIN_ID."""
        with patch.dict(os.environ, {"ADMIN_IDS": "42"}, clear=True):
            config = Config.from_env()
            assert config.admin_ids == [42]
