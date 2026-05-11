"""Tests for Telegram bot module."""

from unittest.mock import AsyncMock

import pytest

from marketplace_assistant.bot.keyboards import back_kb, main_menu_kb, marketplace_kb
from marketplace_assistant.bot.telegram_bot import (
    _format_product,
    create_bot_dispatcher,
    get_user_state,
)


class TestBotKeyboards:
    """Тесты клавиатур бота."""

    def test_main_menu_kb(self):
        """Проверка создания главного меню."""
        kb = main_menu_kb()
        assert kb is not None
        # Проверяем, что есть кнопки
        inline_kb = kb
        assert len(inline_kb.inline_keyboard) > 0

    def test_marketplace_kb(self):
        """Проверка создания клавиатуры выбора площадки."""
        kb = marketplace_kb()
        assert kb is not None

    def test_back_kb(self):
        """Проверка создания кнопки «Назад»."""
        kb = back_kb()
        assert kb is not None


class TestBotHelpers:
    """Тесты вспомогательных функций бота."""

    def test_get_user_state_new(self):
        """Проверка создания нового состояния пользователя."""
        state = get_user_state(999999)
        assert state == {"marketplace": "wb"}

    def test_get_user_state_existing(self):
        """Проверка получения существующего состояния."""
        state = get_user_state(999999)
        state["marketplace"] = "ozon"
        state2 = get_user_state(999999)
        assert state2["marketplace"] == "ozon"

    def test_format_product(self, sample_product_card):
        """Проверка форматирования карточки товара."""
        text = _format_product(sample_product_card)
        assert isinstance(text, str)
        assert sample_product_card.name in text
        assert "Wildberries" in text
        assert "1999" in text
        assert "4.3" in text

    def test_format_product_ozon(self, sample_ozon_product_card):
        """Проверка форматирования карточки Ozon."""
        text = _format_product(sample_ozon_product_card)
        assert "Ozon" in text
        assert "1299" in text


class TestBotDispatcher:
    """Тесты создания диспетчера бота."""

    def test_create_dispatcher_mock_mode(self):
        """Проверка создания диспетчера с mock_mode=True."""
        dp = create_bot_dispatcher(mock_mode=True)
        assert dp is not None

    def test_create_dispatcher_with_keys(self):
        """Проверка создания диспетчера с ключами."""
        dp = create_bot_dispatcher(
            wb_api_key="test-wb-key",
            ozon_client_id="test-client",
            ozon_api_key="test-ozon-key",
            mock_mode=True,
        )
        assert dp is not None


class TestBotCommandHandlers:
    """Тесты обработчиков команд (без реального Telegram)."""

    @pytest.mark.asyncio
    async def test_cmd_start(self):
        """Проверка обработчика /start."""
        dp = create_bot_dispatcher(mock_mode=True)
        message = AsyncMock()
        message.from_user.id = 12345
        message.text = "/start"

        # Симулируем получение сообщения
        # Просто проверяем, что обработчик зарегистрирован
        _routers = dp.sub_routers if hasattr(dp, 'sub_routers') else []
        assert len(dp.sub_routers) > 0 or hasattr(dp, 'message_handlers')

    @pytest.mark.asyncio
    async def test_create_bot_parser_instances(self):
        """Проверка, что бот создаёт парсеры корректно."""
        dp = create_bot_dispatcher(mock_mode=True)
        # Диспетчер должен содержать роутер
        assert hasattr(dp, 'sub_routers')
        assert len(dp.sub_routers) > 0
