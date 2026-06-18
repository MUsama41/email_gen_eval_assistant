from fastapi import APIRouter, Depends

from app.dependencies import get_evaluation_graph
from email_assistant.ai_client.evaluation.graph import EvaluationGraph
from app.schemas.evaluation import EvaluateRequest, EvaluateResponse, MetricScores

router = APIRouter(tags=["evaluation"])


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_email(
    payload: EvaluateRequest,
    graph: EvaluationGraph = Depends(get_evaluation_graph),
) -> EvaluateResponse:
    result = graph.run(
        intent=payload.intent,
        key_facts=payload.key_facts,
        tone=payload.tone,
        subject=payload.subject,
        body=payload.body,
        reference_email=payload.reference_email,
    )
    scores = result["scores"]
    return EvaluateResponse(
        scores=MetricScores(
            fact_recall=scores["fact_recall"],
            tone_accuracy=scores["tone_accuracy"],
            conciseness_fluency=scores["conciseness_fluency"],
            overall=scores["overall"],
        ),
        fact_recall_reason=result["fact_recall_reason"],
        tone_reason=result["tone_reason"],
        fluency_reason=result["fluency_reason"],
    )
