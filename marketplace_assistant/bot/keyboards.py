"""Inline keyboards for Telegram bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск товара", callback_data="menu:product"),
        InlineKeyboardButton(text="📊 Анализ отзывов", callback_data="menu:feedbacks"),
    )
    builder.row(
        InlineKeyboardButton(text="💰 Тренд цены", callback_data="menu:price"),
        InlineKeyboardButton(text="🏆 Конкуренты", callback_data="menu:competitors"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 Сгенерировать описание", callback_data="menu:describe"),
        InlineKeyboardButton(text="❓ Помощь", callback_data="menu:help"),
    )
    return builder.as_markup()


def marketplace_kb() -> InlineKeyboardMarkup:
    """Выбор маркетплейса."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Wildberries", callback_data="mp:wb"),
        InlineKeyboardButton(text="Ozon", callback_data="mp:ozon"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu:back"),
    )
    return builder.as_markup()


def back_kb() -> InlineKeyboardMarkup:
    """Кнопка «Назад»."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu:back"),
    )
    return builder.as_markup()
