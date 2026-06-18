from fastapi import FastAPI

from app.routers import evaluation, generation

app = FastAPI(
    title="Email Generation Assistant",
    version="1.0.0",
    description="Generates professional emails via LangGraph multi-agent graphs on Groq.",
)

app.include_router(generation.router)
app.include_router(evaluation.router)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}
