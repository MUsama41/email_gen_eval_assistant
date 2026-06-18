from typing import List, Optional, TypedDict


class EvaluationState(TypedDict, total=False):
    intent: str
    key_facts: List[str]
    tone: str
    subject: str
    body: str
    reference_email: Optional[str]

    fact_recall_score: float
    fact_recall_reason: str

    tone_score: float
    tone_reason: str

    fluency_score: float
    fluency_reason: str

    overall_score: float
    scores: dict
