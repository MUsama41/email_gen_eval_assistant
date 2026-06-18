import re

FILLER_PHRASES = (
    "just wanted to",
    "i hope this email finds you well",
    "at the end of the day",
    "needless to say",
    "as you may already know",
    "please do not hesitate",
    "in order to",
    "due to the fact that",
)


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def conciseness_score(body: str, min_words: int, max_words: int) -> float:
    count = word_count(body)
    if count < min_words:
        return round(count / min_words, 4) if min_words else 0.0
    if count <= max_words:
        return 1.0
    overflow = count - max_words
    return round(max(0.0, 1.0 - overflow / max_words), 4)


def filler_penalty(body: str) -> float:
    lowered = (body or "").lower()
    hits = sum(1 for phrase in FILLER_PHRASES if phrase in lowered)
    return round(min(1.0, hits * 0.1), 4)


def scale_value(normalized: float, scale: int) -> float:
    return round(normalized * scale, 2)
