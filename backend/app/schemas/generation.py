from typing import List, Optional

from pydantic import BaseModel, Field


class GenerateEmailRequest(BaseModel):
    intent: str = Field(description="The core purpose of the email")
    key_facts: List[str] = Field(description="Bullet points to include in the email")
    tone: str = Field(description="The desired style, such as formal or casual")
    strategy: str = Field(default="advanced", description="advanced or baseline prompting")


class GenerateEmailResponse(BaseModel):
    type: str
    subject: Optional[str] = None
    body: Optional[str] = None
    message: Optional[str] = None
