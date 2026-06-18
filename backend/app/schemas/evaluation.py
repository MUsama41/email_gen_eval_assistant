from typing import List, Optional

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    intent: str
    key_facts: List[str]
    tone: str
    subject: str
    body: str
    reference_email: Optional[str] = None


class MetricScores(BaseModel):
    fact_recall: float
    tone_accuracy: float
    conciseness_fluency: float
    overall: float


class EvaluateResponse(BaseModel):
    scores: MetricScores
    fact_recall_reason: str
    tone_reason: str
    fluency_reason: str
