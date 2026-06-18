import hashlib
import json
import os
from typing import List, Optional

from core.configuration import Settings, get_settings
from core.llm_provider import LLMProvider
from email_assistant.ai_client.email_generation.graph import EmailGenerationGraph
from email_assistant.ai_client.evaluation.graph import EvaluationGraph


class EvaluationRunner:
    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm_provider or LLMProvider(self.settings)
        self.generator = EmailGenerationGraph(self.llm, self.settings)
        self.evaluator = EvaluationGraph(self.llm, self.settings)
        os.makedirs(self.settings.cache_dir, exist_ok=True)

    def load_scenarios(self) -> List[dict]:
        path = os.path.join(self.settings.data_dir, "scenarios.json")
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _cache_path(self, model_name: str, strategy: str, scenario_id: str) -> str:
        key = f"{model_name}|{strategy}|{scenario_id}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return os.path.join(self.settings.cache_dir, f"{digest}.json")

    def _generate_cached(self, scenario: dict, model_name: str, strategy: str) -> dict:
        path = self._cache_path(model_name, strategy, scenario["id"])
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)

        result = self.generator.run(
            intent=scenario["intent"],
            key_facts=scenario["key_facts"],
            tone=scenario["tone"],
            model_name=model_name,
            strategy=strategy,
        )
        response = result.get("response", {})
        email = {
            "subject": response.get("subject", ""),
            "body": response.get("body", response.get("message", "")),
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(email, handle, ensure_ascii=False, indent=2)
        return email

    def run_combo(self, model_name: str, strategy: str) -> List[dict]:
        rows = []
        for scenario in self.load_scenarios():
            email = self._generate_cached(scenario, model_name, strategy)
            evaluation = self.evaluator.run(
                intent=scenario["intent"],
                key_facts=scenario["key_facts"],
                tone=scenario["tone"],
                subject=email["subject"],
                body=email["body"],
                reference_email=scenario.get("reference_email"),
            )
            scores = evaluation["scores"]
            rows.append(
                {
                    "scenario_id": scenario["id"],
                    "intent": scenario["intent"],
                    "tone": scenario["tone"],
                    "model_name": model_name,
                    "strategy": strategy,
                    "subject": email["subject"],
                    "body": email["body"],
                    "fact_recall": scores["fact_recall"],
                    "tone_accuracy": scores["tone_accuracy"],
                    "conciseness_fluency": scores["conciseness_fluency"],
                    "overall": scores["overall"],
                }
            )
        return rows

    @staticmethod
    def averages(rows: List[dict]) -> dict:
        if not rows:
            return {
                "fact_recall": 0.0,
                "tone_accuracy": 0.0,
                "conciseness_fluency": 0.0,
                "overall": 0.0,
            }
        count = len(rows)
        return {
            metric: round(sum(row[metric] for row in rows) / count, 2)
            for metric in ("fact_recall", "tone_accuracy", "conciseness_fluency", "overall")
        }
