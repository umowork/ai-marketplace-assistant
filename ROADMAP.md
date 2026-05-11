# 07 ROADMAP — AI Marketplace Assistant

## MVP (минимально публикуемое)

**Скелет:**
- [ ] FastAPI + aiogram 3 в одном процессе
- [ ] PostgreSQL модели: `Account`, `Product`, `SyncRun`, `GenerationLog`
- [ ] Fernet-шифрование API-токенов с master-ключом в env
- [ ] `/add_account` flow для трёх маркетплейсов

**API-клиенты (Pydantic + httpx):**
- [ ] `WBClient` — Statistics API (заказы, остатки, продажи)
- [ ] `OzonClient` — Seller API (товары, заказы, аналитика)
- [ ] `YandexMarketClient` — Partner API (каталог, цены)
- [ ] Rate-limit middleware для каждого клиента
- [ ] Retry с экспоненциальным бэкоффом

**AI-функции (один сценарий end-to-end):**
- [ ] `/describe <SKU>` — забор характеристик из API → LLM → SEO-описание
- [ ] Структурированный output через `instructor`: title / description / keywords / bullets
- [ ] GigaChat как primary, GPT-4o-mini fallback
- [ ] Сохранение в `GenerationLog` для аналитики

**Деплой и публикация:**
- [ ] Docker compose: FastAPI + bot + Postgres + Redis
- [ ] Deploy на Fly.io
- [ ] README с GIF + Loom 60-90с
- [ ] Tag `v1.0.0`
- [ ] Публичный репозиторий `umawork/ai-marketplace-assistant`

## Расширения (после MVP)

- [ ] `/describe_batch <excel>` — пакетная генерация из Excel
- [ ] `/analyze <query>` — анализ топа выдачи через публичный поиск API
- [ ] `/price <SKU>` — рекомендация цены на основе медианы выдачи
- [ ] `/export weekly` — сводный Excel из 3 кабинетов
- [ ] APScheduler ежедневная синхронизация заказов и остатков
- [ ] `/track <SKU>` + Telegram-alerts при изменениях
- [ ] Streamlit-дашборд динамики продаж

## Stretch

- [ ] **Авито Pro API** — четвёртая площадка
- [ ] **Анализ отзывов** клиента через GigaChat (что хвалят, что ругают)
- [ ] **Прогноз продаж** на основе истории (statsmodels / Prophet)
- [ ] **AI-инфографика** для карточки (Flux / DALL-E)
- [ ] **Webhook-режим** маркетплейсов (если поддерживают) для real-time обновлений

## Релиз

- [ ] Карточка на Kwork: «AI-помощник селлера WB/Ozon — описания, цены»
- [ ] Карточка на FL.ru: расширенная версия с пакетами
- [ ] Пост на vc.ru: «Как мы убрали парсинг и перешли на официальные API маркетплейсов»

## Целевые метрики (замерить и опубликовать)

- [ ] Latency генерации одного SEO-описания (p50 / p95)
- [ ] Cost per SKU (₽ за токены)
- [ ] Стабильность sync (% успешных синхронизаций из 100)
- [ ] CTR описания vs дефолтное (A/B на тестовом аккаунте, если возможно)
