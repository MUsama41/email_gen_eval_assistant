from functools import lru_cache

from core.configuration import get_settings as _get_settings
from core.llm_provider import LLMProvider
from email_assistant.ai_client.email_generation.graph import EmailGenerationGraph
from email_assistant.ai_client.evaluation.graph import EvaluationGraph

get_settings = _get_settings


@lru_cache
def get_llm_provider() -> LLMProvider:
    return LLMProvider()


@lru_cache
def get_email_generation_graph() -> EmailGenerationGraph:
    return EmailGenerationGraph(get_llm_provider())


@lru_cache
def get_evaluation_graph() -> EvaluationGraph:
    return EvaluationGraph(get_llm_provider())
