"""Telegram bot handlers for AI Marketplace Assistant.

Использует aiogram 3.x. Команды и callback-обработчики.
"""


from aiogram import Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from marketplace_assistant.analytics.summarizer import summarize_feedbacks
from marketplace_assistant.analytics.trends import analyze_price_trend
from marketplace_assistant.bot.keyboards import back_kb, main_menu_kb, marketplace_kb
from marketplace_assistant.models.product import ProductCard
from marketplace_assistant.parsers.ozon import OzonParser
from marketplace_assistant.parsers.wildberries import WildberriesParser
from marketplace_assistant.utils.cache import MemoryCache
from marketplace_assistant.utils.logger import get_logger

logger = get_logger(__name__)

# User state (simple storage for demo purposes)
_user_state: dict[int, dict] = {}


def get_user_state(user_id: int) -> dict:
    """Получить состояние пользователя."""
    if user_id not in _user_state:
        _user_state[user_id] = {"marketplace": "wb"}
    return _user_state[user_id]


def create_bot_dispatcher(
    wb_api_key: str = "",
    ozon_client_id: str = "",
    ozon_api_key: str = "",
    mock_mode: bool = True,
) -> Dispatcher:
    """Создать диспетчер aiogram с обработчиками.

    Args:
        wb_api_key: API-ключ WB Seller API.
        ozon_client_id: Client ID Ozon Seller API.
        ozon_api_key: API-ключ Ozon Seller API.
        mock_mode: Использовать мок-данные если True.

    Returns:
        Настроенный Dispatcher.
    """
    dp = Dispatcher()
    router = Router()

    # Lazy parsers (создаются при первом использовании)
    cache = MemoryCache()

    def get_wb_parser() -> WildberriesParser:
        return WildberriesParser(
            api_key=wb_api_key,
            mock_mode=mock_mode,
            cache=cache,
        )

    def get_ozon_parser() -> OzonParser:
        return OzonParser(
            client_id=ozon_client_id,
            api_key=ozon_api_key,
            mock_mode=mock_mode,
            cache=cache,
        )

    # ===== Command Handlers =====

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        """Обработчик команды /start."""
        user_id = message.from_user.id
        get_user_state(user_id)

        await message.answer(
            "🛒 <b>AI Marketplace Assistant</b>\n\n"
            "Помогаю анализировать товары на Wildberries и Ozon:\n"
            "🔍 Карточки товаров\n"
            "📊 Отзывы и тональность\n"
            "💰 Тренды цены\n"
            "🏆 Анализ конкурентов\n"
            "🤖 SEO-описания\n\n"
            "Выберите действие:",
            reply_markup=main_menu_kb(),
        )

    @router.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        """Обработчик команды /help."""
        await message.answer(
            "🛒 <b>AI Marketplace Assistant</b>\n\n"
            "<b>Команды:</b>\n"
            "/start — главное меню\n"
            "/product <артикул> — карточка товара\n"
            "/feedbacks <артикул> — анализ отзывов\n"
            "/price <артикул> — тренд цены\n"
            "/competitors <запрос> — поиск конкурентов\n"
            "/describe <название> — SEO-описание\n"
            "/marketplace wb|ozon — выбрать площадку\n"
            "/help — эта справка\n\n"
            "📌 По умолчанию: Wildberries (wb). "
            "Используйте /marketplace для смены.",
            reply_markup=main_menu_kb(),
        )

    @router.message(Command("marketplace"))
    async def cmd_marketplace(message: Message) -> None:
        """Обработчик команды /marketplace — выбор площадки."""
        args = message.text.split()
        if len(args) >= 2:
            mp = args[1].lower()
            if mp in ("wb", "ozon"):
                state = get_user_state(message.from_user.id)
                state["marketplace"] = mp
                mp_name = "Wildberries" if mp == "wb" else "Ozon"
                await message.answer(f"✅ Площадка изменена на <b>{mp_name}</b>")
                return

        await message.answer(
            "Выберите площадку:",
            reply_markup=marketplace_kb(),
        )

    @router.message(Command("product"))
    async def cmd_product(message: Message) -> None:
        """Обработчик команды /product <article>."""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "Использование: /product <артикул>\n"
                "Пример: /product 12345678"
            )
            return

        article = args[1].strip()
        state = get_user_state(message.from_user.id)
        mp = state["marketplace"]

        msg = await message.answer(f"🔍 Ищу товар {article} на {'WB' if mp == 'wb' else 'Ozon'}...")

        try:
            if mp == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            product = await parser.get_product_card(article)
            await msg.edit_text(_format_product(product))
        except Exception as e:
            logger.error("Product fetch error: %s", e)
            await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

    @router.message(Command("feedbacks"))
    async def cmd_feedbacks(message: Message) -> None:
        """Обработчик команды /feedbacks <article>."""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "Использование: /feedbacks <артикул>\n"
                "Пример: /feedbacks 12345678"
            )
            return

        article = args[1].strip()
        state = get_user_state(message.from_user.id)
        mp = state["marketplace"]

        msg = await message.answer(f"📊 Анализирую отзывы для {article}...")

        try:
            if mp == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            feedbacks = await parser.get_feedbacks(article, limit=100)
            summary = await summarize_feedbacks(feedbacks, article, mp)

            text = (
                f"📊 <b>Анализ отзывов</b>\n"
                f"Товар: {article} ({'WB' if mp == 'wb' else 'Ozon'})\n\n"
                f"⭐ Средняя оценка: {summary.average_rating}/5\n"
                f"📝 Всего отзывов: {summary.total_reviews}\n"
                f"🎯 Тональность: {summary.overall_sentiment}\n\n"
            )

            if summary.top_positive_themes:
                text += "✅ <b>Что нравится:</b>\n"
                for t in summary.top_positive_themes[:5]:
                    text += f"  • {t}\n"

            if summary.top_complaints:
                text += "\n❌ <b>Жалобы:</b>\n"
                for c in summary.top_complaints[:5]:
                    text += f"  • {c}\n"

            await msg.edit_text(text[:4000])
        except Exception as e:
            logger.error("Feedbacks error: %s", e)
            await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

    @router.message(Command("price"))
    async def cmd_price(message: Message) -> None:
        """Обработчик команды /price <article>."""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "Использование: /price <артикул>\n"
                "Пример: /price 12345678"
            )
            return

        article = args[1].strip()
        state = get_user_state(message.from_user.id)
        mp = state["marketplace"]

        msg = await message.answer(f"💰 Анализирую тренд цены для {article}...")

        try:
            if mp == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            price_history = await parser.get_price_history(article)
            product = await parser.get_product_card(article)
            trend = await analyze_price_trend(price_history, product.price)

            emoji = {"up": "📈", "down": "📉", "stable": "➡️"}.get(trend.trend_direction, "➡️")

            text = (
                f"💰 <b>Тренд цены</b>\n"
                f"Товар: {product.name[:50]}\n"
                f"Артикул: {article}\n\n"
                f"💵 Текущая цена: {float(trend.current_price):.0f} ₽\n"
                f"{emoji} Тренд: {trend.trend_direction}\n"
                f"📊 Изменение: {trend.price_change_percent:+.1f}%\n"
                f"📈 Макс: {float(trend.max_price):.0f} ₽\n"
                f"📉 Мин: {float(trend.min_price):.0f} ₽\n"
                f"📊 Средняя: {float(trend.avg_price):.0f} ₽\n"
                f"📆 Проанализировано дней: {trend.days_analyzed}"
            )

            await msg.edit_text(text)
        except Exception as e:
            logger.error("Price trend error: %s", e)
            await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

    @router.message(Command("competitors"))
    async def cmd_competitors(message: Message) -> None:
        """Обработчик команды /competitors <query>."""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "Использование: /competitors <поисковый запрос>\n"
                "Пример: /competitors наушники"
            )
            return

        query = args[1].strip()
        state = get_user_state(message.from_user.id)
        mp = state["marketplace"]

        msg = await message.answer(f"🏆 Ищу конкурентов по запросу «{query}»...")

        try:
            if mp == "ozon":
                parser = get_ozon_parser()
            else:
                parser = get_wb_parser()

            competitors = await parser.search_competitors(query, limit=10)

            if not competitors:
                await msg.edit_text("❌ Конкуренты не найдены.")
                return

            text = f"🏆 <b>Конкуренты</b> ({'WB' if mp == 'wb' else 'Ozon'})\n"
            text += f"Запрос: «{query}»\n\n"

            for i, comp in enumerate(competitors[:10], 1):
                text += (
                    f"{i}. {comp.name[:40]}\n"
                    f"   💰 {float(comp.price):.0f} ₽"
                )
                if comp.rating:
                    text += f" | ⭐ {comp.rating}"
                if comp.reviews_count:
                    text += f" | 📝 {comp.reviews_count} отзывов"
                text += "\n"

            await msg.edit_text(text[:4000])
        except Exception as e:
            logger.error("Competitors error: %s", e)
            await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

    @router.message(Command("describe"))
    async def cmd_describe(message: Message) -> None:
        """Обработчик команды /describe <name>."""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "Использование: /describe <название товара>\n"
                "Пример: /describe Беспроводные наушники"
            )
            return

        product_name = args[1].strip()
        msg = await message.answer(f"🤖 Генерирую описание для «{product_name}»...")

        # Генерация описания (мок или LLM)
        description = (
            f"✨ {product_name} — лучший выбор для вашего комфорта!\n\n"
            f"🔹 Преимущества:\n"
            f"• Высокое качество материалов\n"
            f"• Современный дизайн\n"
            f"• Быстрая доставка\n\n"
            f"🛒 Закажите прямо сейчас!"
        )

        await msg.edit_text(description)

    # ===== Callback Handlers =====

    @router.callback_query(F.data.startswith("menu:"))
    async def menu_callback(callback: CallbackQuery) -> None:
        """Обработчик callback'ов главного меню."""
        action = callback.data.replace("menu:", "")

        if action == "back":
            await callback.message.edit_text(
                "🛒 <b>AI Marketplace Assistant</b>\n\n"
                "Выберите действие:",
                reply_markup=main_menu_kb(),
            )
        elif action == "help":
            await callback.message.edit_text(
                "🛒 <b>AI Marketplace Assistant</b>\n\n"
                "<b>Команды:</b>\n"
                "/product <артикул> — карточка товара\n"
                "/feedbacks <артикул> — анализ отзывов\n"
                "/price <артикул> — тренд цены\n"
                "/competitors <запрос> — конкуренты\n"
                "/describe <название> — описание\n"
                "/marketplace wb|ozon — выбор площадки\n"
                "/help — помощь",
                reply_markup=back_kb(),
            )
        elif action == "product":
            await callback.message.edit_text(
                "🔍 Введите артикул товара:\n"
                "Пример: <code>/product 12345678</code>",
                reply_markup=back_kb(),
            )
        elif action == "feedbacks":
            await callback.message.edit_text(
                "📊 Введите артикул для анализа отзывов:\n"
                "Пример: <code>/feedbacks 12345678</code>",
                reply_markup=back_kb(),
            )
        elif action == "price":
            await callback.message.edit_text(
                "💰 Введите артикул для анализа тренда цены:\n"
                "Пример: <code>/price 12345678</code>",
                reply_markup=back_kb(),
            )
        elif action == "competitors":
            await callback.message.edit_text(
                "🏆 Введите поисковый запрос для поиска конкурентов:\n"
                "Пример: <code>/competitors наушники</code>",
                reply_markup=back_kb(),
            )
        elif action == "describe":
            await callback.message.edit_text(
                "🤖 Введите название товара для генерации описания:\n"
                "Пример: <code>/describe Беспроводные наушники</code>",
                reply_markup=back_kb(),
            )
        else:
            await callback.message.edit_text(
                "Неизвестное действие.",
                reply_markup=main_menu_kb(),
            )

        await callback.answer()

    @router.callback_query(F.data.startswith("mp:"))
    async def marketplace_callback(callback: CallbackQuery) -> None:
        """Обработчик выбора маркетплейса."""
        mp = callback.data.replace("mp:", "")
        state = get_user_state(callback.from_user.id)
        state["marketplace"] = mp
        mp_name = "Wildberries" if mp == "wb" else "Ozon"

        await callback.message.edit_text(
            f"✅ Выбрана площадка: <b>{mp_name}</b>\n\n"
            "Теперь используйте команды:\n"
            "/product <артикул>\n"
            "/feedbacks <артикул>\n"
            "/price <артикул>\n"
            "/competitors <запрос>",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()

    dp.include_router(router)
    return dp


def _format_product(product: ProductCard) -> str:
    """Форматировать карточку товара для Telegram."""
    mp_name = "Wildberries" if product.marketplace == "wb" else "Ozon"
    lines = [
        f"📦 <b>{product.name}</b>",
        f"🏪 {mp_name} | Артикул: {product.article}",
        "",
    ]

    if product.brand:
        lines.append(f"🏷️ Бренд: {product.brand}")
    if product.category:
        lines.append(f"📂 Категория: {product.category}")

    lines.append("")
    lines.append(f"💰 Цена: {float(product.price):.0f} ₽")
    if product.old_price and product.old_price > product.price:
        lines.append(f"🏷️ Старая цена: {float(product.old_price):.0f} ₽")
        old_p = float(product.old_price)
        new_p = float(product.price)
        discount = ((old_p - new_p) / old_p) * 100
        lines.append(f"🔥 Скидка: {discount:.0f}%")

    if product.rating:
        stars = "⭐" * int(round(product.rating))
        lines.append(f"{stars} {product.rating}/5 ({product.reviews_count} отзывов)")

    if product.stock:
        lines.append(f"📦 Остаток: {product.stock} шт.")

    if product.characteristics:
        lines.append("")
        lines.append("📋 Характеристики:")
        for k, v in list(product.characteristics.items())[:10]:
            lines.append(f"  • {k}: {v}")

    if product.description:
        desc = product.description[:200]
        lines.append(f"\n📝 {desc}")

    return "\n".join(lines)
