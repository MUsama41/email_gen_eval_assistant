import logging
import os
from typing import Optional, Tuple, Type, TypeVar

import instructor
from groq import Groq
from openai import OpenAI
from pydantic import BaseModel

from core.configuration import Settings, get_settings

logger = logging.getLogger(__name__)

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)

DEFAULT_PROVIDER = "groq"


class ProviderConfigError(RuntimeError):
    pass


class LLMProvider:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._configure_tracing()
        self._clients: dict = {}

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

    @staticmethod
    def _split_model(model: str) -> Tuple[str, str]:
        if ":" in model:
            provider, model_id = model.split(":", 1)
            return provider.strip().lower(), model_id.strip()
        return DEFAULT_PROVIDER, model.strip()

    def _build_client(self, provider: str):
        if provider == "groq":
            if not self._settings.groq_api_key:
                raise ProviderConfigError("GROQ_API_KEY is not set.")
            base = Groq(api_key=self._settings.groq_api_key)
            return instructor.from_groq(base, mode=instructor.Mode.TOOLS)

        if provider == "gemini":
            if not self._settings.gemini_api_key:
                raise ProviderConfigError("GEMINI_API_KEY is not set.")
            base = OpenAI(
                api_key=self._settings.gemini_api_key,
                base_url=self._settings.gemini_base_url,
            )
            return instructor.from_openai(base, mode=instructor.Mode.JSON)

        if provider == "cerebras":
            if not self._settings.cerebras_api_key:
                raise ProviderConfigError("CEREBRAS_API_KEY is not set.")
            base = OpenAI(
                api_key=self._settings.cerebras_api_key,
                base_url=self._settings.cerebras_base_url,
            )
            return instructor.from_openai(base, mode=instructor.Mode.TOOLS)

        if provider == "openrouter":
            if not self._settings.openrouter_api_key:
                raise ProviderConfigError("OPENROUTER_API_KEY is not set.")
            base = OpenAI(
                api_key=self._settings.openrouter_api_key,
                base_url=self._settings.openrouter_base_url,
            )
            return instructor.from_openai(base, mode=instructor.Mode.TOOLS)

        raise ProviderConfigError(f"Unknown provider '{provider}'.")

    def _client_for(self, provider: str):
        if provider not in self._clients:
            logger.info("Initializing client for provider '%s'", provider)
            self._clients[provider] = self._build_client(provider)
        return self._clients[provider]

    def generate(
        self,
        model_name: str,
        system_prompt: str,
        human_prompt: str,
        response_model: Type[ResponseModelT],
        temperature: Optional[float] = None,
    ) -> ResponseModelT:
        provider, model_id = self._split_model(model_name)
        client = self._client_for(provider)
        resolved_temperature = (
            temperature if temperature is not None else self._settings.gen_temperature
        )
        return client.chat.completions.create(
            model=model_id,
            response_model=response_model,
            temperature=resolved_temperature,
            max_tokens=self._settings.max_tokens,
            max_retries=self._settings.llm_max_retries,
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
