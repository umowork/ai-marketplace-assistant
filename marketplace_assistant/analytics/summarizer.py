"""Feedback summarization module — выделяет топ-темы, жалобы, ключевые инсайты."""

import re
from collections import Counter

from marketplace_assistant.models.feedback import Feedback, FeedbackSummary
from marketplace_assistant.utils.logger import get_logger

logger = get_logger(__name__)

# Стоп-слова для исключения из ключевых тем
STOP_WORDS: set[str] = {
    "это", "что", "как", "все", "она", "он", "они", "его", "ее", "её",
    "для", "нас", "вас", "вам", "нам", "кто", "где", "когда", "потом",
    "потому", "поэтому", "зачем", "почему", "тоже", "также", "очень",
    "вот", "уже", "еще", "ещё", "можно", "надо", "нужно", "будет",
    "быть", "есть", "был", "была", "было", "были", "бы", "но", "и",
    "а", "или", "да", "нет", "не", "ни", "в", "на", "с", "со", "к",
    "ко", "от", "ото", "до", "по", "за", "про", "об", "обо", "из",
    "изо", "у", "о", "при", "без", "безо", "через", "сквозь", "между",
    "над", "под", "перед", "после", "вокруг", "около", "возле", "мимо",
    "против", "ради", "кроме", "вместо", "вроде", "насчет", "несмотря",
    "благодаря", "ввиду", "вследствие",
}

COMMON_COMPLAINT_TRIGGERS: list[str] = [
    r"не\s+работает", r"сломал", r"брак", r"дефект", r"царапин",
    r"не\s+подо[шл]", r"возврат", r"не\s+соответствует", r"обман",
    r"пло[х]?о", r"ужасн", r"некачеств", r"испорчен",
    r"разбил", r"оторвал", r"сломан", r"неудобн", r"маленьк",
    r"больш[о]?[й]?", r"размер", r"не\s+тот", r"цвет",
    r"доставк", r"долг", r"задержк", r"упаковк",
    r"инструкци", r"непонятн", r"сложн", r"не\s+понравил",
]


async def summarize_feedbacks(
    feedbacks: list[Feedback],
    article: str,
    marketplace: str,
    llm_analytics: object | None = None,
) -> FeedbackSummary:
    """Суммаризировать отзывы — выделить топ-темы, жалобы, тональность.

    Args:
        feedbacks: Список отзывов.
        article: Артикул товара.
        marketplace: Маркетплейс.
        llm_analytics: Опциональный LLM-анализатор для улучшенной суммаризации.

    Returns:
        FeedbackSummary с аналитикой.
    """
    if not feedbacks:
        return FeedbackSummary(
            article=article,
            marketplace=marketplace,
            total_reviews=0,
            average_rating=0.0,
            summary_short="Нет отзывов для анализа.",
        )

    total = len(feedbacks)
    avg_rating = sum(f.rating for f in feedbacks) / total
    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for f in feedbacks:
        dist[f.rating] = dist.get(f.rating, 0) + 1

    # Выделяем ключевые темы
    all_text = " ".join(f.text for f in feedbacks if f.text).lower()
    words = re.findall(r"[а-яёa-z]+", all_text)
    word_freq = Counter(
        w for w in words if w not in STOP_WORDS and len(w) > 3
    )
    top_positive_themes = _extract_positive_themes(word_freq, feedbacks)
    top_complaints = _extract_complaints(feedbacks)

    # Определяем общую тональность
    positive_ratio = (dist.get(5, 0) + dist.get(4, 0)) / total
    negative_ratio = (dist.get(1, 0) + dist.get(2, 0)) / total

    if positive_ratio > 0.7:
        overall_sentiment = "positive"
    elif negative_ratio > 0.4:
        overall_sentiment = "negative"
    else:
        overall_sentiment = "neutral"

    # Краткая сводка
    summary_short = _generate_short_summary(
        avg_rating, total, overall_sentiment, top_positive_themes, top_complaints
    )

    return FeedbackSummary(
        article=article,
        marketplace=marketplace,
        total_reviews=total,
        average_rating=round(avg_rating, 2),
        rating_distribution=dist,
        top_positive_themes=top_positive_themes[:5],
        top_complaints=top_complaints[:5],
        overall_sentiment=overall_sentiment,
        summary_short=summary_short,
    )


def _extract_positive_themes(
    word_freq: Counter, feedbacks: list[Feedback]
) -> list[str]:
    """Извлечь позитивные темы из отзывов."""
    positive_signals = {
        "качество", "доставка", "цена", "удобно", "красивый", "быстро",
        "надежный", "хороший", "отличный", "удобный", "стильный",
        "компактный", "легкий", "функциональный", "размер", "цвет",
        "материал", "упаковка", "сервис", "рекомендую",
    }

    # Ищем частые темы среди слов с позитивным контекстом
    themes = []
    for word, count in word_freq.most_common(20):
        if word in positive_signals and count >= 2:
            if word == "доставка":
                themes.append("🚚 Быстрая доставка")
            elif word == "качество":
                themes.append("⭐ Высокое качество")
            elif word == "цена":
                themes.append("💰 Доступная цена")
            elif word == "удобно" or word == "удобный":
                themes.append("👍 Удобство использования")
            elif word in ("красивый", "стильный"):
                themes.append("🎨 Привлекательный дизайн")
            elif word == "быстро":
                themes.append("⚡ Быстрая обработка заказа")
            elif word in ("надежный", "хороший", "отличный"):
                themes.append(f"✅ {word.capitalize()} товар")
            else:
                themes.append(word.capitalize())

    # Fallback: если не нашли, берём из текстов отзывов с высоким рейтингом
    if not themes:
        for fb in sorted(feedbacks, key=lambda x: x.rating, reverse=True)[:3]:
            if fb.pros:
                themes.extend(t.strip() for t in fb.pros.split(",") if t.strip())

    return themes


def _extract_complaints(feedbacks: list[Feedback]) -> list[str]:
    """Извлечь топ жалоб из отзывов."""
    complaints_counter: Counter = Counter()

    for fb in feedbacks:
        # Низкие оценки — источник жалоб
        if fb.rating <= 3 and fb.text:
            text_lower = fb.text.lower()
            for trigger in COMMON_COMPLAINT_TRIGGERS:
                if re.search(trigger, text_lower):
                    # Нормализуем триггер в читаемую жалобу
                    complaint = _normalize_complaint(trigger)
                    if complaint:
                        complaints_counter[complaint] += 1

        # Из поля cons
        if fb.cons:
            for cons_part in fb.cons.split(";"):
                cons_part = cons_part.strip().lower()
                if cons_part and len(cons_part) > 2:
                    complaints_counter[cons_part] += 1

    return [c for c, _ in complaints_counter.most_common(10)]


def _normalize_complaint(trigger: str) -> str | None:
    """Нормализовать regex-триггер в читаемую жалобу."""
    mapping = {
        r"не\s+работает": "❌ Товар не работает",
        r"сломал": "🔧 Товар ломается",
        r"брак": "⚠️ Брак",
        r"дефект": "⚠️ Дефект товара",
        r"царапин": "🔍 Царапины / повреждения",
        r"не\s+подо[шл]": "📏 Не подошёл по размеру",
        r"возврат": "🔄 Оформление возврата",
        r"не\s+соответствует": "📋 Не соответствует описанию",
        r"обман": "🚫 Обман / введение в заблуждение",
        r"пло[х]?о": "👎 Плохое качество",
        r"ужасн": "😡 Ужасное качество",
        r"некачеств": "👎 Некачественный товар",
        r"испорчен": "⚠️ Испорченный товар",
        r"разбил": "💔 Товар разбился",
        r"оторвал": "🔧 Отрываются детали",
        r"неудобн": "😕 Неудобно в использовании",
        r"маленьк": "📏 Маленький размер",
        r"больш[о]?[й]?": "📏 Большой размер",
        r"размер": "📏 Проблемы с размером",
        r"не\s+тот": "📦 Не тот товар",
        r"цвет": "🎨 Несоответствие цвета",
        r"доставк": "🚚 Проблемы с доставкой",
        r"долг": "⏱️ Долгая доставка",
        r"задержк": "⏱️ Задержка доставки",
        r"упаковк": "📦 Проблемы с упаковкой",
        r"инструкци": "📄 Непонятная инструкция",
        r"сложн": "🤔 Сложно в использовании",
        r"не\s+понравил": "👎 Не понравился товар",
    }
    return mapping.get(trigger)


def _generate_short_summary(
    avg_rating: float,
    total: int,
    sentiment: str,
    positive_themes: list[str],
    complaints: list[str],
) -> str:
    """Сгенерировать краткую текстовую сводку."""
    sentiment_emoji = {
        "positive": "🟢",
        "negative": "🔴",
        "neutral": "🟡",
    }
    emoji = sentiment_emoji.get(sentiment, "⚪")
    parts = [
        f"{emoji} Средняя оценка: {avg_rating:.1f} / 5 ({total} отзывов).",
    ]

    if positive_themes:
        parts.append(f"✅ Что нравится: {', '.join(positive_themes[:3])}.")
    if complaints:
        parts.append(f"❌ Основные жалобы: {', '.join(complaints[:3])}.")

    return " ".join(parts)
