"""Main entry point for AI Marketplace Assistant.

Запускает FastAPI сервер и Telegram бота конкурентно.
"""

import asyncio
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config
from marketplace_assistant.api.fastapi_app import create_app
from marketplace_assistant.bot.telegram_bot import create_bot_dispatcher
from marketplace_assistant.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def start_api(config: Config) -> None:
    """Запустить FastAPI сервер."""
    # lazy import uvicorn
    import uvicorn

    logger.info(
        "Starting API on %s:%d (mock_mode=%s)",
        config.host,
        config.port,
        config.mock_mode,
    )
    app = create_app(
        wb_api_key=config.wb_api_key,
        ozon_client_id=config.ozon_client_id,
        ozon_api_key=config.ozon_api_key,
        llm_api_key=config.llm_api_key,
        llm_model=config.llm_model,
        llm_provider=config.llm_provider,
        mock_mode=config.mock_mode,
        redis_url=config.redis_url,
    )
    uvicorn_config = uvicorn.Config(
        app,
        host=config.host,
        port=config.port,
        log_level="debug" if config.debug else "info",
    )
    server = uvicorn.Server(uvicorn_config)
    await server.serve()


async def start_bot(config: Config) -> None:
    """Запустить Telegram бота."""
    if not config.bot_token:
        logger.warning("BOT_TOKEN not set, skipping Telegram bot")
        return

    logger.info(
        "Starting Telegram bot (mock_mode=%s)",
        config.mock_mode,
    )

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_bot_dispatcher(
        wb_api_key=config.wb_api_key,
        ozon_client_id=config.ozon_client_id,
        ozon_api_key=config.ozon_api_key,
        mock_mode=config.mock_mode,
    )
    await dp.start_polling(bot)


async def main() -> None:
    """Главная функция — запуск API и бота."""
    setup_logging()
    config = Config.from_env()

    logger.info(
        "🚀 AI Marketplace Assistant v0.2.0 starting...\n"
        "   Mock mode: %s\n"
        "   LLM: %s/%s\n"
        "   WB API: %s\n"
        "   Ozon API: %s\n"
        "   Redis: %s",
        config.mock_mode,
        config.llm_provider,
        config.llm_model,
        "configured" if config.wb_api_key else "not configured",
        "configured" if config.ozon_api_key else "not configured",
        config.redis_url or "not configured",
    )

    tasks = []

    if config.bot_token:
        tasks.append(start_bot(config))
    else:
        logger.info("Telegram bot disabled (no BOT_TOKEN)")

    # API запускается всегда (даже без бота)
    tasks.append(start_api(config))

    if not tasks:
        logger.error("Nothing to run! Set at least BOT_TOKEN or enable API.")
        sys.exit(1)

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
