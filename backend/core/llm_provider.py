import os
from typing import Optional, Type, TypeVar

import instructor
from groq import Groq
from pydantic import BaseModel

from core.configuration import Settings, get_settings

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class LLMProvider:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._configure_tracing()
        base_client = Groq(api_key=self._settings.groq_api_key)
        self._client = instructor.from_groq(base_client, mode=instructor.Mode.TOOLS)

    def _configure_tracing(self) -> None:
        if not self._settings.langsmith_tracing:
            return
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_ENDPOINT"] = self._settings.langsmith_endpoint
        os.environ["LANGCHAIN_ENDPOINT"] = self._settings.langsmith_endpoint
        if self._settings.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = self._settings.langsmith_api_key
            os.environ["LANGCHAIN_API_KEY"] = self._settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = self._settings.langsmith_project
        os.environ["LANGCHAIN_PROJECT"] = self._settings.langsmith_project

    def generate(
        self,
        model_name: str,
        system_prompt: str,
        human_prompt: str,
        response_model: Type[ResponseModelT],
        temperature: Optional[float] = None,
    ) -> ResponseModelT:
        resolved_temperature = (
            temperature if temperature is not None else self._settings.gen_temperature
        )
        return self._client.chat.completions.create(
            model=model_name,
            response_model=response_model,
            temperature=resolved_temperature,
            max_tokens=self._settings.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": human_prompt},
            ],
        )

    def judge(
        self,
        system_prompt: str,
        human_prompt: str,
        response_model: Type[ResponseModelT],
    ) -> ResponseModelT:
        return self.generate(
            model_name=self._settings.judge_model,
            system_prompt=system_prompt,
            human_prompt=human_prompt,
            response_model=response_model,
            temperature=self._settings.judge_temperature,
        )
