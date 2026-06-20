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
