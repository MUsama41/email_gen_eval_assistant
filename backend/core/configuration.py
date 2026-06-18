from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = Field(default="")

    langsmith_tracing: bool = Field(default=False)
    langsmith_endpoint: str = Field(default="https://api.smith.langchain.com")
    langsmith_api_key: str = Field(default="")
    langsmith_project: str = Field(default="email_assistant")

    model_a: str = Field(default="llama-3.3-70b-versatile")
    model_b: str = Field(default="llama-3.1-8b-instant")
    judge_model: str = Field(default="openai/gpt-oss-120b")

    gen_temperature: float = Field(default=0.4)
    judge_temperature: float = Field(default=0.0)
    max_tokens: int = Field(default=1024)

    score_scale: int = Field(default=100)

    conciseness_min_words: int = Field(default=60)
    conciseness_max_words: int = Field(default=220)

    metric_weight_fact_recall: float = Field(default=0.4)
    metric_weight_tone: float = Field(default=0.3)
    metric_weight_fluency: float = Field(default=0.3)

    data_dir: str = Field(default="data")
    results_dir: str = Field(default="results")
    cache_dir: str = Field(default=".cache")

    @property
    def metric_weights(self) -> dict:
        return {
            "fact_recall": self.metric_weight_fact_recall,
            "tone": self.metric_weight_tone,
            "fluency": self.metric_weight_fluency,
        }

    @property
    def generation_models(self) -> dict:
        return {"model_a": self.model_a, "model_b": self.model_b}


@lru_cache
def get_settings() -> Settings:
    return Settings()
