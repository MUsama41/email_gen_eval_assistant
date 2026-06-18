from email_assistant.utils import (
    conciseness_score,
    filler_penalty,
    scale_value,
    word_count,
)


def test_word_count_counts_words():
    assert word_count("Dear Team, thank you.") == 4


def test_word_count_handles_empty():
    assert word_count("") == 0


def test_conciseness_in_band_is_full():
    body = " ".join(["word"] * 100)
    assert conciseness_score(body, 60, 220) == 1.0


def test_conciseness_below_band_scales_down():
    body = " ".join(["word"] * 30)
    assert 0.0 < conciseness_score(body, 60, 220) < 1.0


def test_conciseness_above_band_penalized():
    body = " ".join(["word"] * 440)
    assert conciseness_score(body, 60, 220) < 1.0


def test_filler_penalty_detects_phrases():
    body = "I just wanted to reach out. I hope this email finds you well."
    assert filler_penalty(body) > 0.0


def test_filler_penalty_clean_text_is_zero():
    assert filler_penalty("Thank you for the update.") == 0.0


def test_scale_value_to_100():
    assert scale_value(0.5, 100) == 50.0
