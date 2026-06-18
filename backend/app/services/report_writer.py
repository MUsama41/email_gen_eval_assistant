import json
import os
from typing import List, Optional

import pandas as pd

from app.services.metric_definitions import METRIC_DEFINITIONS
from core.configuration import Settings, get_settings


class ReportWriter:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        os.makedirs(self.settings.results_dir, exist_ok=True)

    def _path(self, filename: str) -> str:
        return os.path.join(self.settings.results_dir, filename)

    def write_combo(self, model_name: str, strategy: str, rows: List[dict], averages: dict) -> dict:
        safe_model = model_name.replace("/", "_")
        stem = f"eval_{safe_model}_{strategy}"

        df = pd.DataFrame(rows)
        csv_path = self._path(f"{stem}.csv")
        df.to_csv(csv_path, index=False)

        payload = {
            "model_name": model_name,
            "strategy": strategy,
            "metric_definitions": METRIC_DEFINITIONS,
            "raw_scores": rows,
            "averages": averages,
        }
        json_path = self._path(f"{stem}.json")
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

        return {"csv": csv_path, "json": json_path}

    def write_comparison(self, summary_rows: List[dict]) -> str:
        df = pd.DataFrame(summary_rows)
        path = self._path("comparison.csv")
        df.to_csv(path, index=False)
        return path
