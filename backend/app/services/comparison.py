import logging
from typing import List, Optional

from app.services.evaluation_runner import DailyLimitReached, EvaluationRunner
from app.services.report_writer import ReportWriter
from core.configuration import Settings, get_settings

logger = logging.getLogger(__name__)

STRATEGIES = ("advanced", "baseline")


class ComparisonService:
    def __init__(
        self,
        runner: Optional[EvaluationRunner] = None,
        writer: Optional[ReportWriter] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.runner = runner or EvaluationRunner(settings=self.settings)
        self.writer = writer or ReportWriter(self.settings)

    def _combos(self) -> List[dict]:
        combos = []
        for model_name in (self.settings.model_a, self.settings.model_b):
            for strategy in STRATEGIES:
                combos.append({"model_name": model_name, "strategy": strategy})
        return combos

    def run(self) -> dict:
        combos = self._combos()
        summary_rows = []
        stopped_early = False
        for combo_index, combo in enumerate(combos, start=1):
            logger.info(
                "=== Combo %d/%d: model=%s strategy=%s ===",
                combo_index,
                len(combos),
                combo["model_name"],
                combo["strategy"],
            )
            try:
                rows = self.runner.run_combo(combo["model_name"], combo["strategy"])
            except DailyLimitReached:
                logger.error(
                    "Daily token cap reached during combo %d/%d. Writing the combos "
                    "completed so far; re-run after the quota resets to finish.",
                    combo_index,
                    len(combos),
                )
                stopped_early = True
                break

            averages = self.runner.averages(rows)
            paths = self.writer.write_combo(
                combo["model_name"], combo["strategy"], rows, averages
            )
            logger.info("Wrote %s and %s", paths["csv"], paths["json"])
            summary_rows.append(
                {
                    "model_name": combo["model_name"],
                    "strategy": combo["strategy"],
                    **averages,
                }
            )

        self.writer.write_comparison(summary_rows)
        winner = max(summary_rows, key=lambda row: row["overall"]) if summary_rows else None
        return {"summary": summary_rows, "winner": winner, "stopped_early": stopped_early}
