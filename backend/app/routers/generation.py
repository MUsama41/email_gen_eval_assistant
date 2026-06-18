from fastapi import APIRouter, Depends

from app.dependencies import get_email_generation_graph, get_settings
from email_assistant.ai_client.email_generation.graph import EmailGenerationGraph
from app.schemas.generation import GenerateEmailRequest, GenerateEmailResponse
from core.configuration import Settings

router = APIRouter(tags=["generation"])


@router.post("/generate", response_model=GenerateEmailResponse)
def generate_email(
    payload: GenerateEmailRequest,
    graph: EmailGenerationGraph = Depends(get_email_generation_graph),
    settings: Settings = Depends(get_settings),
) -> GenerateEmailResponse:
    model_name = settings.model_a if payload.strategy == "advanced" else settings.model_b
    result = graph.run(
        intent=payload.intent,
        key_facts=payload.key_facts,
        tone=payload.tone,
        model_name=model_name,
        strategy=payload.strategy,
    )
    response = result.get("response", {})
    return GenerateEmailResponse(
        type=response.get("type", "ERROR"),
        subject=response.get("subject"),
        body=response.get("body"),
        message=response.get("message"),
    )
