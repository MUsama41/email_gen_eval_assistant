import hashlib
import json
import logging
import os
import time
from typing import List, Optional

from core.configuration import Settings, get_settings
from core.llm_provider import LLMProvider
from email_assistant.ai_client.email_generation.graph import EmailGenerationGraph
from email_assistant.ai_client.evaluation.graph import EvaluationGraph

logger = logging.getLogger(__name__)

DAILY_LIMIT_MARKERS = ("per day", "tpd", "tokens per day")


class DailyLimitReached(Exception):
    pass


def _is_daily_limit(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text and any(marker in text for marker in DAILY_LIMIT_MARKERS)


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
        key = f"row|{model_name}|{strategy}|{scenario_id}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return os.path.join(self.settings.cache_dir, f"{digest}.json")

    def _read_cached_row(self, model_name: str, strategy: str, scenario_id: str) -> Optional[dict]:
        path = self._cache_path(model_name, strategy, scenario_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        return None

    def _write_cached_row(self, model_name: str, strategy: str, scenario_id: str, row: dict) -> None:
        path = self._cache_path(model_name, strategy, scenario_id)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(row, handle, ensure_ascii=False, indent=2)

    def _pace(self) -> None:
        delay = self.settings.inter_call_delay_seconds
        if delay > 0:
            time.sleep(delay)

    def _score_scenario(self, scenario: dict, model_name: str, strategy: str) -> dict:
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
        self._pace()

        evaluation = self.evaluator.run(
            intent=scenario["intent"],
            key_facts=scenario["key_facts"],
            tone=scenario["tone"],
            subject=email["subject"],
            body=email["body"],
            reference_email=scenario.get("reference_email"),
        )
        scores = evaluation["scores"]
        return {
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

    def run_combo(self, model_name: str, strategy: str) -> List[dict]:
        scenarios = self.load_scenarios()
        logger.info(
            "Running combo model=%s strategy=%s over %d scenarios",
            model_name,
            strategy,
            len(scenarios),
        )
        rows = []
        for index, scenario in enumerate(scenarios, start=1):
            scenario_id = scenario["id"]
            cached = self._read_cached_row(model_name, strategy, scenario_id)
            if cached is not None:
                logger.info(
                    "  [%d/%d] %s cached overall=%s",
                    index,
                    len(scenarios),
                    scenario_id,
                    cached.get("overall"),
                )
                rows.append(cached)
                continue

            try:
                logger.info(
                    "  [%d/%d] %s generating + evaluating...",
                    index,
                    len(scenarios),
                    scenario_id,
                )
                row = self._score_scenario(scenario, model_name, strategy)
                self._write_cached_row(model_name, strategy, scenario_id, row)
                rows.append(row)
                logger.info(
                    "  [%d/%d] %s done overall=%s",
                    index,
                    len(scenarios),
                    scenario_id,
                    row["overall"],
                )
                self._pace()
            except Exception as error:
                if _is_daily_limit(error):
                    logger.error(
                        "  [%d/%d] %s hit a DAILY token cap. Stopping; %d scenarios "
                        "are cached. Re-run after the quota resets to resume.",
                        index,
                        len(scenarios),
                        scenario_id,
                        len(rows),
                    )
                    raise DailyLimitReached(str(error)) from error
                logger.exception(
                    "  [%d/%d] %s FAILED; skipping",
                    index,
                    len(scenarios),
                    scenario_id,
                )
        logger.info(
            "Combo model=%s strategy=%s complete: %d/%d scenarios scored",
            model_name,
            strategy,
            len(rows),
            len(scenarios),
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
