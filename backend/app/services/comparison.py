from typing import List, Optional

from app.services.evaluation_runner import EvaluationRunner
from app.services.report_writer import ReportWriter
from core.configuration import Settings, get_settings

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
        summary_rows = []
        for combo in self._combos():
            rows = self.runner.run_combo(combo["model_name"], combo["strategy"])
            averages = self.runner.averages(rows)
            self.writer.write_combo(combo["model_name"], combo["strategy"], rows, averages)
            summary_rows.append(
                {
                    "model_name": combo["model_name"],
                    "strategy": combo["strategy"],
                    **averages,
                }
            )

        self.writer.write_comparison(summary_rows)
        winner = max(summary_rows, key=lambda row: row["overall"]) if summary_rows else None
        return {"summary": summary_rows, "winner": winner}
