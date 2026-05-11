"""LLM-аналитика через instructor / OpenAI / GigaChat.

Использует instructor для структурированного вывода (Pydantic models).
Поддерживает OpenAI и GigaChat.
"""


from marketplace_assistant.models.feedback import (
    Feedback,
    FeedbackSummary,
    SentimentResult,
)
from marketplace_assistant.utils.logger import get_logger

logger = get_logger(__name__)


class LLMAnalytics:
    """LLM-аналитика для анализа отзывов и генерации контента.

    Использует instructor для строго типизированного вывода от LLM.
    Поддерживает OpenAI-совместимые API и GigaChat.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        provider: str = "openai",
        mock_mode: bool = True,
    ):
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.mock_mode = mock_mode
        self._client = None

    async def _get_client(self):
        """Ленивая инициализация клиента instructor."""
        if self._client is not None:
            return self._client
        try:
            import instructor
            from openai import AsyncOpenAI

            if self.provider == "gigachat":
                # GigaChat через OpenAI-совместимый API
                openai_client = AsyncOpenAI(
                    base_url="https://gigachat.devices.sberbank.ru/api/v1",
                    api_key=self.api_key,
                )
            else:
                openai_client = AsyncOpenAI(api_key=self.api_key)

            self._client = instructor.from_openai(openai_client)
            logger.info(
                "LLM client initialized: provider=%s model=%s",
                self.provider,
                self.model,
            )
            return self._client
        except ImportError as e:
            logger.warning("instructor not installed: %s", e)
            return None
        except Exception as e:
            logger.warning("Failed to init LLM client: %s", e)
            return None

    async def analyze_sentiment(self, text: str) -> SentimentResult:
        """Анализ тональности текста через LLM."""
        if self.mock_mode:
            return SentimentResult(
                text_hash=str(hash(text) % 10**16),
                sentiment=(
                    "positive"
                    if "хорош" in text.lower() or "отлич" in text.lower()
                    else "neutral"
                ),
                score=0.5 if "хорош" in text.lower() or "отлич" in text.lower() else 0.0,
                keywords=[],
                language="ru",
            )

        client = await self._get_client()
        if client is None:
            raise RuntimeError("LLM client not available")

        try:
            result, _ = await client.chat.completions.create_with_completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — анализатор тональности. "
                            "Определи тональность текста (positive/negative/neutral), "
                            "оценку от -1 до 1, ключевые слова и язык."
                        ),
                    },
                    {"role": "user", "content": f"Проанализируй тональность: {text}"},
                ],
                response_model=SentimentResult,
            )
            return result
        except Exception as e:
            logger.error("LLM sentiment analysis failed: %s", e)
            raise

    async def summarize_feedbacks_llm(
        self, feedbacks: list[Feedback], article: str, marketplace: str
    ) -> FeedbackSummary:
        """Суммаризация отзывов через LLM.

        Args:
            feedbacks: Список отзывов для анализа.
            article: Артикул товара.
            marketplace: Маркетплейс.

        Returns:
            FeedbackSummary со структурированным выводом от LLM.
        """
        if self.mock_mode or not feedbacks:
            # Fallback через подсчёт
            total = len(feedbacks)
            avg_rating = sum(f.rating for f in feedbacks) / total if total else 0
            dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for f in feedbacks:
                dist[f.rating] = dist.get(f.rating, 0) + 1
            return FeedbackSummary(
                article=article,
                marketplace=marketplace,
                total_reviews=total,
                average_rating=round(avg_rating, 2),
                rating_distribution=dist,
                overall_sentiment="positive" if avg_rating >= 4 else "neutral",
                summary_short=f"Средняя оценка: {avg_rating:.1f} / 5 ({total} отзывов).",
            )

        client = await self._get_client()
        if client is None:
            raise RuntimeError("LLM client not available")

        # Подготовка текстов отзывов для LLM
        feedbacks_text = "\n\n".join(
            f"Оценка {f.rating}: {f.text}"
            + (f"\nДостоинства: {f.pros}" if f.pros else "")
            + (f"\nНедостатки: {f.cons}" if f.cons else "")
            for f in feedbacks[:50]  # Ограничиваем 50 отзывов
        )

        try:
            result, _ = await client.chat.completions.create_with_completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — аналитик маркетплейсов. "
                            "Проанализируй отзывы на товар и верни структурированную сводку. "
                            "Выдели топ-5 позитивных тем, топ-5 жалоб. "
                            "Определи общую тональность. Напиши краткую сводку на русском."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Проанализируй отзывы на товар (артикул {article}, {marketplace}):\n\n"
                            f"{feedbacks_text}"
                        ),
                    },
                ],
                response_model=FeedbackSummary,
            )
            result.article = article
            result.marketplace = marketplace
            return result
        except Exception as e:
            logger.error("LLM summarization failed: %s", e)
            raise

    async def generate_description(
        self,
        product_name: str,
        features: list[str],
        marketplace: str = "wb",
    ) -> str:
        """Сгенерировать SEO-описание товара через LLM."""
        if self.mock_mode:
            return (
                f"✨ {product_name} — лучший выбор!\n\n"
                f"🔹 Характеристики: {', '.join(features)}\n\n"
                f"✅ Высокое качество\n"
                f"✅ Быстрая доставка\n"
                f"✅ Гарантия 12 месяцев\n\n"
                f"[Сгенерировано через LLM]"
            )

        client = await self._get_client()
        if client is None:
            raise RuntimeError("LLM client not available")

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — копирайтер для маркетплейсов. "
                            f"Напиши SEO-описание для {marketplace.upper()} "
                            "на русском языке. Используй эмодзи, выдели преимущества. "
                            "Длина: 200-300 символов."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Товар: {product_name}\n"
                            f"Характеристики: {', '.join(features)}\n"
                            f"Маркетплейс: {marketplace}"
                        ),
                    },
                ],
                temperature=0.7,
                max_tokens=500,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM description generation failed: %s", e)
            raise

    async def improve_card(
        self, product_card: dict, marketplace: str = "wb"
    ) -> dict:
        """Улучшить карточку товара с помощью LLM (название, описание, характеристики)."""
        if self.mock_mode:
            return {
                **product_card,
                "improved_name": f"{product_card.get('name', '')} [улучшено]",
                "improved_description": "Улучшенное SEO-описание товара для маркетплейса.",
                "suggestions": [
                    "Добавьте ключевые слова в название",
                    "Улучшите фотографии",
                ],
            }

        client = await self._get_client()
        if client is None:
            raise RuntimeError("LLM client not available")

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — эксперт по оптимизации карточек товаров для маркетплейсов. "
                            "Предложи улучшения для названия, описания и характеристик."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Улучши карточку товара для {marketplace}:\n{product_card}",
                    },
                ],
                temperature=0.5,
                max_tokens=800,
            )
            return {
                **product_card,
                "llm_suggestions": response.choices[0].message.content or "",
            }
        except Exception as e:
            logger.error("LLM card improvement failed: %s", e)
            raise
