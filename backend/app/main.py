from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import comparison, evaluation, generation

app = FastAPI(
    title="Email Generation Assistant",
    version="1.0.0",
    description="Generates professional emails via LangGraph graphs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generation.router)
app.include_router(evaluation.router)
app.include_router(comparison.router)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}
