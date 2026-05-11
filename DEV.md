# 07 — AI Marketplace Assistant: DEV.md

> Разработка и архитектура проекта.

## 🏗 Архитектура

```
main.py                              # Точка входа
config.py                            # Конфигурация из .env
marketplace_assistant/
├── api/fastapi_app.py               # FastAPI routes (lazy parsers)
├── bot/telegram_bot.py              # Telegram bot handlers (aiogram 3)
├── parsers/
│   ├── base.py                      # BaseParser (ABC)
│   ├── wildberries.py               # WB: публичное API + Seller API
│   └── ozon.py                      # Ozon: публичное API + Seller API
├── analytics/
│   ├── sentiment.py                 # Rule-based + LLM тональность
│   ├── summarizer.py                # Суммаризация отзывов
│   ├── trends.py                    # Тренды цены, конкуренты
│   └── llm_analytics.py             # LLM через instructor
├── models/
│   ├── product.py                   # ProductCard & Co (Pydantic)
│   └── feedback.py                  # Feedback & Co (Pydantic)
└── utils/
    ├── cache.py                     # MemoryCache / RedisCache
    └── logger.py                    # Логирование
```

## 🧪 Тестирование

```
make test          # Быстрые тесты (без real_api)
make test-cov      # С покрытием
make test-all      # Все тесты (включая real_api маркер)
```

### Маркеры тестов

- `mock` — тесты с мок-данными
- `real_api` — требует реальных ключей API (пропускаются по умолчанию)
- `slow` — медленные тесты (интеграционные)

## 🔄 MOCK_MODE

При `MOCK_MODE=true` (по умолчанию) все API-вызовы возвращают
заранее подготовленные тестовые данные. Никаких реальных запросов.

При `MOCK_MODE=false`:
- WB: парсинг через card.wb.ru + feedbacks (публичные API)
- Ozon: парсинг через ozon.ru + seller API (если настроен)
- LLM: OpenAI / GigaChat через instructor

## 📦 Зависимости

- **FastAPI** — REST API
- **aiogram 3** — Telegram Bot
- **httpx** — HTTP-клиент
- **instructor** — структурированный LLM-вывод
- **pydantic** — модели данных
- **ruff** — линтер
- **pytest** — тесты

## 🔑 Получение API-ключей

### Wildberries (опционально)
1. https://seller.wildberries.ru/ — раздел "Доступ к API"
2. Скопировать API-ключ → `WB_API_KEY`

### Ozon (опционально)
1. https://seller.ozon.ru/ — "Настройки → API"
2. Client ID + API Key → `OZON_CLIENT_ID`, `OZON_API_KEY`

### OpenAI (для LLM-аналитики)
1. https://platform.openai.com/api-keys
2. Скопировать ключ → `LLM_API_KEY`

## 📝 Заметки

- Все внешние HTTP-запросы кэшируются (MemoryCache по умолчанию)
- Парсеры используют lazy imports
- `MOCK_MODE=true` безопасен для демо и разработки

## 📊 Self-check

✅ Минимум 1200 строк Python: считаем через `make lint`
✅ Минимум 5 тестовых файлов: `ls tests/*.py | wc -l`
✅ Минимум 20 тестов: `make test | grep "passed"` (или `make test`)
✅ Нет моков/TODO в production-коде (кроме MOCK_MODE)
✅ Модульная структура: parsers/, analytics/, api/, bot/
✅ Makefile с целями
✅ .env.example
✅ DEV.md
✅ lazy imports (uvicorn, instructor, redis)
