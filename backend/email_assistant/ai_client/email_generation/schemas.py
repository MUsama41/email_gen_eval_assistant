from typing import Optional

from pydantic import BaseModel, Field


class InputValidationParser(BaseModel):
    is_valid: bool = Field(description="Whether the inputs are sufficient to write an email")
    reason: Optional[str] = Field(default=None, description="Why the inputs are insufficient")


class OutlineParser(BaseModel):
    outline: str = Field(description="A short plan mapping intent, facts, and tone to the email")


class DraftParser(BaseModel):
    subject: str = Field(description="The email subject line")
    body: str = Field(description="The full email body")


class CritiqueParser(BaseModel):
    needs_revision: bool = Field(description="Whether the draft should be revised")
    critique: str = Field(description="Specific, actionable issues to fix")
