from abc import ABC, abstractmethod
from typing import Any, Optional

from langgraph.graph import StateGraph

from core.configuration import Settings, get_settings
from core.llm_provider import LLMProvider


class BaseGraph(ABC):
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm_provider or LLMProvider(self.settings)
        self._compiled = None

    @abstractmethod
    def _build(self) -> StateGraph:
        raise NotImplementedError

    def compile(self):
        if self._compiled is None:
            self._compiled = self._build().compile()
        return self._compiled

    def invoke(self, initial_state: dict) -> dict:
        return self.compile().invoke(initial_state)


def render(template: str, **values: Any) -> str:
    return template.format(**values)
