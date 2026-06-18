from pydantic import BaseModel, Field


class FactRecallParser(BaseModel):
    covered_facts: int = Field(description="How many key facts are accurately present")
    total_facts: int = Field(description="Total number of key facts provided")
    fabricated: bool = Field(description="Whether the email invents facts not provided")
    reason: str = Field(description="Brief justification")


class ToneParser(BaseModel):
    alignment: float = Field(description="Tone match from 0.0 to 1.0")
    detected_tone: str = Field(description="The tone perceived in the email")
    reason: str = Field(description="Brief justification")


class FluencyParser(BaseModel):
    fluency: float = Field(description="Grammar and readability from 0.0 to 1.0")
    reason: str = Field(description="Brief justification")
