from core.configuration import Settings
from email_assistant.ai_client.email_generation.graph import EmailGenerationGraph
from email_assistant.ai_client.email_generation.schemas import (
    CritiqueParser,
    DraftParser,
    InputValidationParser,
    OutlineParser,
)
from email_assistant.ai_client.evaluation.graph import EvaluationGraph
from email_assistant.ai_client.evaluation.schemas import (
    FactRecallParser,
    FluencyParser,
    ToneParser,
)


class FakeLLM:
    def generate(self, model_name, system_prompt, human_prompt, response_model, temperature=None):
        return self._fake(response_model)

    def judge(self, system_prompt, human_prompt, response_model):
        return self._fake(response_model)

    @staticmethod
    def _fake(response_model):
        if response_model is InputValidationParser:
            return InputValidationParser(is_valid=True, reason=None)
        if response_model is OutlineParser:
            return OutlineParser(outline="Open, body, close.")
        if response_model is DraftParser:
            return DraftParser(subject="Test Subject", body="Dear Team, thank you. Best regards.")
        if response_model is CritiqueParser:
            return CritiqueParser(needs_revision=False, critique="")
        if response_model is FactRecallParser:
            return FactRecallParser(covered_facts=2, total_facts=2, fabricated=False, reason="ok")
        if response_model is ToneParser:
            return ToneParser(alignment=0.9, detected_tone="formal", reason="ok")
        if response_model is FluencyParser:
            return FluencyParser(fluency=0.9, reason="ok")
        raise AssertionError(f"Unexpected response_model: {response_model}")


def _settings():
    return Settings(groq_api_key="test", langsmith_tracing=False)


def test_email_generation_graph_reaches_package():
    graph = EmailGenerationGraph(FakeLLM(), _settings())
    result = graph.run(
        intent="Follow up",
        key_facts=["Discussed roadmap", "Sync Friday"],
        tone="formal",
        model_name="llama-3.3-70b-versatile",
        strategy="advanced",
    )
    assert result["response"]["type"] == "EMAIL"
    assert result["response"]["subject"] == "Test Subject"


def test_email_generation_baseline_skips_critique():
    graph = EmailGenerationGraph(FakeLLM(), _settings())
    result = graph.run(
        intent="Follow up",
        key_facts=["Discussed roadmap"],
        tone="casual",
        model_name="llama-3.1-8b-instant",
        strategy="baseline",
    )
    assert result["response"]["type"] == "EMAIL"


def test_evaluation_graph_aggregates_scores():
    graph = EvaluationGraph(FakeLLM(), _settings())
    result = graph.run(
        intent="Follow up",
        key_facts=["Discussed roadmap", "Sync Friday"],
        tone="formal",
        subject="Test Subject",
        body=" ".join(["word"] * 100),
    )
    scores = result["scores"]
    assert 0 <= scores["overall"] <= 100
    assert scores["fact_recall"] == 100.0
    assert set(scores.keys()) == {
        "fact_recall",
        "tone_accuracy",
        "conciseness_fluency",
        "overall",
    }
