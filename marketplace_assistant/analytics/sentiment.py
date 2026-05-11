"""Sentiment analysis module.

Поддерживает:
- Встроенный rule-based анализатор тональности для русского языка
- Интеграцию с LLM (если настроена)
"""

import hashlib
import re

from marketplace_assistant.models.feedback import SentimentResult
from marketplace_assistant.utils.logger import get_logger

logger = get_logger(__name__)

# Встроенные словари тональности для русского языка
POSITIVE_WORDS: set[str] = {
    "отлично", "хорошо", "прекрасно", "замечательно", "отличный", "хороший",
    "качественный", "удобный", "красивый", "стильный", "доволен", "довольна",
    "нравится", "понравился", "понравилась", "супер", "топ", "класс", "классный",
    "круто", "крутой", "шикарный", "великолепный", "впечатляет", "рекомендую",
    "спасибо", "благодарю", "стоит", "достойный", "надежный", "быстрый",
    "легкий", "компактный", "функциональный", "качество", "довольны", "покупкой",
    "лучший", "отличная", "отличное", "хорошая", "хорошее", "удобная",
    "удобное", "красивая", "красивое", "качественная", "качественное",
    "понравилось", "нравился", "нравилась", "нравилось", "радует",
    "доставка", "быстро", "качественно", "аккуратно",
}

NEGATIVE_WORDS: set[str] = {
    "плохо", "плохой", "ужасно", "ужасный", "отвратительный", "кошмар",
    "некачественный", "брак", "сломался", "сломалась", "сломали", "сломано",
    "не работает", "неработает", "не работал", "дефект", "царапина",
    "обман", "не соответствует", "несоответствует", "возврат", "вернул",
    "вернула", "не подошел", "не подошла", "не подошло", "неудобный",
    "неудобная", "неудобное", "некрасивый", "дешёвый", "дешевый",
    "хрупкий", "сломанный", "сломанная", "сломанное", "порвался",
    "порвалась", "разбился", "разбилась", "испорчен", "испорчена",
    "ужасное", "ужасная", "отвратительное", "отвратительная", "кошмарный",
    "кошмарная", "кошмарное", "некачественная", "некачественное",
    "перестал", "перестала", "гарантия", "проблема",
    "проблемы", "неприятный", "неприятная", "неприятное", "разочарован",
    "разочарована", "разочарование", "жалоба", "претензия", "недоволен",
    "недовольна", "ужас", "катастрофа", "кошмарно",
}

INTENSIFIERS: set[str] = {
    "очень", "сильно", "крайне", "чрезвычайно", "абсолютно", "полностью",
    "совсем", "совершенно", "весьма", r"з\s*",
}


def _hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]


async def analyze_sentiment(
    text: str, llm_analytics: object | None = None
) -> SentimentResult:
    """Анализ тональности текста.

    Использует rule-based метод для русского языка.
    Если передан llm_analytics — использует LLM для более точного анализа.
    """
    text_lower = text.lower()
    text_hash = _hash_text(text)

    # Если есть LLM — используем её для точного анализа
    if llm_analytics is not None:
        try:
            return await llm_analytics.analyze_sentiment(text)
        except Exception as e:
            logger.warning("LLM sentiment failed, falling back to rules: %s", e)

    # Rule-based анализ
    words = re.findall(r"[а-яёa-z]+", text_lower)
    word_set = set(words)

    positive_count = sum(1 for w in word_set if w in POSITIVE_WORDS)
    negative_count = sum(1 for w in word_set if w in NEGATIVE_WORDS)

    # Учёт интенсификаторов
    intensity = 1.0
    for token in text_lower.split():
        if token in INTENSIFIERS:
            intensity = 1.5
            break

    total = positive_count + negative_count
    if total == 0:
        return SentimentResult(
            text_hash=text_hash,
            sentiment="neutral",
            score=0.0,
            keywords=[],
            language="ru",
        )

    raw_score = (positive_count - negative_count) / max(total, 1) * intensity
    score = max(-1.0, min(1.0, raw_score))

    if score > 0.2:
        sentiment = "positive"
    elif score < -0.2:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    keywords = list(word_set.intersection(POSITIVE_WORDS | NEGATIVE_WORDS))

    return SentimentResult(
        text_hash=text_hash,
        sentiment=sentiment,
        score=round(score, 4),
        keywords=keywords[:10],
        language="ru",
    )


async def analyze_feedbacks_sentiment(
    texts: list[str],
    llm_analytics: object | None = None,
) -> list[SentimentResult]:
    """Пакетный анализ тональности списка текстов."""
    results = []
    for text in texts:
        result = await analyze_sentiment(text, llm_analytics)
        results.append(result)
    return results
