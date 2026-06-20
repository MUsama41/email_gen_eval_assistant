import csv
import glob
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.comparison import ComparisonService
from core.configuration import get_settings

router = APIRouter(tags=["comparison"])


class ComparisonResponse(BaseModel):
    summary: list
    winner: Optional[dict]
    stopped_early: bool


@router.get("/comparison/results", response_model=ComparisonResponse)
def get_comparison_results() -> ComparisonResponse:
    settings = get_settings()
    csv_path = os.path.join(settings.results_dir, "comparison.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="No results found. Use POST /comparison to run the evaluation.")
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "model_name": row["model_name"],
                "strategy": row["strategy"],
                "fact_recall": float(row["fact_recall"]),
                "tone_accuracy": float(row["tone_accuracy"]),
                "conciseness_fluency": float(row["conciseness_fluency"]),
                "overall": float(row["overall"]),
            })
    winner = max(rows, key=lambda r: r["overall"]) if rows else None
    return ComparisonResponse(summary=rows, winner=winner, stopped_early=False)


@router.post("/comparison", response_model=ComparisonResponse)
def run_comparison(force: bool = Query(default=False)) -> ComparisonResponse:
    try:
        if force:
            settings = get_settings()
            for path in glob.glob(os.path.join(settings.cache_dir, "*.json")):
                os.remove(path)
        service = ComparisonService()
        result = service.run()
        return ComparisonResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
