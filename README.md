# AI Marketplace Assistant

> 🛒 AI-ассистент для селлеров Wildberries и Ozon: аналитика карточек, отзывов, конкурентов и цен.

## Возможности

- 🔍 **Сбор данных карточек товаров** WB/Ozon по артикулу (публичные API)
- 📊 **Анализ отзывов**: тональность, топ-темы, жалобы
- 💰 **Тренд цены**: история изменения цены, волатильность
- 🏆 **Анализ конкурентов**: позиционирование по цене и рейтингу
- 🤖 **LLM-аналитика**: генерация SEO-описаний, улучшение карточек (через instructor)
- 📱 **Telegram Bot** + **FastAPI** одновременно

## Быстрый старт

```bash
cp .env.example .env
# Отредактируйте .env (как минимум BOT_TOKEN)

pip install -r requirements.txt
python main.py
```

## Docker

```bash
docker-compose up -d
```

## API Endpoints

| Метод | Путь | Описание |
|-------|------|---------|
| GET | `/health` | Health check |
| GET | `/product` | Карточка товара |
| GET | `/feedbacks` | Отзывы на товар |
| GET | `/analyze-feedbacks` | Аналитика отзывов |
| GET | `/price-trend` | Тренд цены |
| GET | `/competitors` | Анализ конкурентов |
| GET | `/market-insights` | Комплексная аналитика |
| POST | `/generate-description` | SEO-описание через LLM |

## Telegram команды

- `/start` — главное меню
- `/product <артикул>` — карточка товара
- `/feedbacks <артикул>` — анализ отзывов
- `/price <артикул>` — тренд цены
- `/competitors <запрос>` — конкуренты
- `/describe <название>` — SEO-описание
- `/marketplace wb|ozon` — выбрать площадку

## Структура проекта

```
marketplace_assistant/
├── api/           # FastAPI routes и Pydantic модели
│   ├── fastapi_app.py
│   └── models.py
├── bot/           # Telegram бот (aiogram 3)
│   ├── telegram_bot.py
│   └── keyboards.py
├── parsers/       # Сбор данных маркетплейсов (публичные API)
│   ├── base.py        # Абстрактный базовый класс
│   ├── wildberries.py # WB: публичный API + Seller API
│   ├── ozon.py        # Ozon: публичный API + Seller API
│   └── errors.py
├── analytics/     # Аналитические модули
│   ├── sentiment.py    # Тональный анализ
│   ├── summarizer.py   # Суммаризация отзывов
│   ├── trends.py       # Тренды цены и рынка
│   └── llm_analytics.py # LLM через instructor
├── models/        # Pydantic доменные модели
│   ├── product.py
│   └── feedback.py
└── utils/         # Утилиты
    ├── cache.py    # Кэширование (Redis/Memory)
    └── logger.py   # Логирование
```

## Переменные окружения

Все переменные — в файле `.env.example`.

Ключевые:
- `MOCK_MODE=true` — мок-данные (без реальных API)
- `BOT_TOKEN` — токен Telegram бота
- `LLM_API_KEY` — ключ OpenAI/GigaChat
- `WB_API_KEY` — ключ WB Seller API
- `OZON_CLIENT_ID` / `OZON_API_KEY` — ключи Ozon Seller API

## Лицензия

MIT
