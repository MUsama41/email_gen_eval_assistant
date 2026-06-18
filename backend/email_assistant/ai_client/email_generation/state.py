from typing import List, Optional, TypedDict


class EmailGenerationState(TypedDict, total=False):
    intent: str
    key_facts: List[str]
    tone: str
    model_name: str
    strategy: str

    is_valid: bool
    validation_reason: Optional[str]

    outline: str
    subject: str
    body: str

    critique: str
    needs_revision: bool

    response: dict
