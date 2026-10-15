"""Provider-neutral messages and evidence-grounded interaction mapping."""
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Message(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    sent_at: datetime
    text: str
    reply_to_message_id: str | None = None

    @model_validator(mode="after")
    def check_aware(self):
        if self.sent_at.tzinfo is None or self.sent_at.utcoffset() is None:
            raise ValueError("sent_at must include timezone")
        return self


class LocalInteraction(BaseModel):
    """LLM output. It NEVER supplies a durable interaction identifier."""
    local_key: str
    message_ids: list[str] = Field(min_length=1)
    topic: str
    summary: str
    participants: list[str] = Field(default_factory=list)


class MappingDraft(BaseModel):
    interactions: list[LocalInteraction]
    unassigned_message_ids: list[str] = Field(default_factory=list)


class Interaction(BaseModel):
    id: str
    chat_id: str
    message_ids: list[str]
    topic: str
    summary: str
    participants: list[str]
    first_evidence_at: datetime
    last_evidence_at: datetime


class MappingResult(BaseModel):
    interactions: list[Interaction]
    unassigned_message_ids: list[str]
    unresolved_local_keys: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
