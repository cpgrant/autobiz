from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_type: Literal["goal", "metric", "risk", "work_item", "opportunity"]
    record_id: str


class ManagementSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=240)
    rationale: str = Field(min_length=1, max_length=2000)
    function: Literal["direction", "growth", "delivery", "finance", "operations"]
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=5)


class ManagementLoopOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2000)
    suggestions: list[ManagementSuggestionOutput] = Field(min_length=1, max_length=3)


class OperationsEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_type: Literal["operating_cycle", "metric", "risk", "work_item"]
    record_id: str


class OperationsSuggestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=240)
    rationale: str = Field(min_length=1, max_length=2000)
    function: Literal["delivery", "operations"]
    evidence: list[OperationsEvidenceReference] = Field(min_length=1, max_length=5)


class OperationsLoopOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2000)
    exceptions: list[str] = Field(max_length=5)
    suggestions: list[OperationsSuggestionOutput] = Field(min_length=1, max_length=3)


class CustomerEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_type: Literal["customer_request", "offer", "engagement", "deliverable"]
    record_id: str


class CustomerDraftOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1, max_length=3000)
    intent: Literal["acknowledge", "clarify", "offer_follow_up", "delivery_update"]
    escalation_reason: str | None = Field(default=None, max_length=500)
    evidence: list[CustomerEvidenceReference] = Field(min_length=1, max_length=5)


class CustomerLoopOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1000)
    drafts: list[CustomerDraftOutput] = Field(min_length=1, max_length=2)
