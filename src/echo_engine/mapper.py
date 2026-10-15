"""Narrow semantic mapper; the LLM groups messages but does not control identity."""
from __future__ import annotations
import json
from typing import Protocol, Sequence
from .models import Message, MappingDraft


SYSTEM_PROMPT = """You map messages to concurrent interactions (semantic threads), NOT risks.
A group chat can have interleaved exchanges about different subjects. Group by conversational continuity,
not temporal adjacency. A message may participate in more than one interaction when it genuinely bridges
threads. Do not hallucinate messages, participants, or replies. Use only the supplied stable message IDs.
Include ordinary conversations; assign ambiguous messages to unassigned_message_ids rather than guessing.
Do not infer intent, danger, or severity. Output valid JSON matching the requested schema.
Each interaction contains a local_key (only unique inside this call), message_ids, topic,
summary, participants (sender IDs). All input messages should be assigned or explicitly unassigned.
"""


class SemanticMapper(Protocol):
    def map(self, messages: Sequence[Message]) -> MappingDraft: ...


class OpenAIMapper:
    """Optional production adapter. Install echo-interactions[llm]."""
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        from openai import OpenAI
        self.client = OpenAI()
        self.model = model

    def map(self, messages: Sequence[Message]) -> MappingDraft:
        if not messages:
            return MappingDraft(interactions=[], unassigned_message_ids=[])
        payload = [{"id": m.id, "sender_id": m.sender_id, "sent_at": m.sent_at.isoformat(),
                    "text": m.text, "reply_to_message_id": m.reply_to_message_id} for m in messages]
        response = self.client.responses.create(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=json.dumps({"messages": payload}, ensure_ascii=False),
            text={"format": {"type": "json_schema", "name": "interaction_mapping",
                "strict": True, "schema": {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "interactions": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                            "properties": {"local_key": {"type": "string"}, "message_ids": {"type": "array", "items": {"type": "string"}},
                                           "topic": {"type": "string"}, "summary": {"type": "string"},
                                           "participants": {"type": "array", "items": {"type": "string"}}},
                            "required": ["local_key", "message_ids", "topic", "summary", "participants"]}},
                        "unassigned_message_ids": {"type": "array", "items": {"type": "string"}}},
                    "required": ["interactions", "unassigned_message_ids"]}}},
        )
        return MappingDraft.model_validate_json(response.output_text)
