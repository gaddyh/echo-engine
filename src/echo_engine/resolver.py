"""Deterministic, conservative identity resolution backed by an in-memory store.

Storage is intentionally an interface. A production Postgres adapter can provide transactionally
serialized updates per chat. This implementation is for evaluation and CLI replay.
"""
from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from typing import Sequence
from .models import Message, Interaction, MappingDraft, MappingResult


class InteractionStore:
    def __init__(self) -> None:
        self._by_chat: dict[str, dict[str, Interaction]] = {}

    def list(self, chat_id: str) -> list[Interaction]:
        return list(self._by_chat.get(chat_id, {}).values())

    def save(self, interaction: Interaction) -> None:
        self._by_chat.setdefault(interaction.chat_id, {})[interaction.id] = interaction


class InteractionResolver:
    def __init__(self, store: InteractionStore) -> None:
        self.store = store

    def resolve(self, messages: Sequence[Message], draft: MappingDraft) -> MappingResult:
        if not messages:
            if draft.interactions or draft.unassigned_message_ids:
                raise ValueError("draft references messages but input is empty")
            return MappingResult(interactions=[], unassigned_message_ids=[])
        chat_ids = {m.chat_id for m in messages}
        if len(chat_ids) != 1:
            raise ValueError("all messages must be in one chat")
        chat_id = next(iter(chat_ids))
        by_id = {m.id: m for m in messages}
        if len(by_id) != len(messages):
            raise ValueError("duplicate message IDs")
        used: set[str] = set()
        keys: set[str] = set()
        for local in draft.interactions:
            if local.local_key in keys:
                raise ValueError("duplicate local_key")
            keys.add(local.local_key)
            if len(set(local.message_ids)) != len(local.message_ids):
                raise ValueError("duplicate evidence ID in one interaction")
            if not set(local.message_ids) <= by_id.keys():
                raise ValueError("unknown evidence message ID")
            if not set(local.participants) <= {by_id[mid].sender_id for mid in local.message_ids}:
                raise ValueError("participants must be senders of cited messages")
            used.update(local.message_ids)
        if not set(draft.unassigned_message_ids) <= by_id.keys():
            raise ValueError("unknown unassigned message ID")
        if used & set(draft.unassigned_message_ids):
            raise ValueError("message cannot be both assigned and unassigned")
        if used | set(draft.unassigned_message_ids) != by_id.keys():
            raise ValueError("every input message must be assigned or unassigned")

        existing = self.store.list(chat_id)
        reserved_ids: set[str] = set()
        result: list[Interaction] = []
        unresolved: list[str] = []
        diagnostics: list[str] = []
        for local in draft.interactions:
            evidence = set(local.message_ids)
            overlapping = [old for old in existing if evidence & set(old.message_ids)]
            # A shared ID is sufficient only if it identifies exactly one prior thread.
            # Two old threads sharing evidence is ambiguous: never merge them automatically.
            if len(overlapping) > 1 or (len(overlapping) == 1 and overlapping[0].id in reserved_ids):
                unresolved.append(local.local_key)
                diagnostics.append(f"ambiguous_identity:{local.local_key}")
                continue
            prior = overlapping[0] if overlapping else None
            # No overlap does not establish semantic continuity. Create a fresh identity.
            # A future candidate matcher may explicitly relate non-overlapping threads.
            ids = evidence | (set(prior.message_ids) if prior else set())
            times = [by_id[i].sent_at for i in evidence]
            prior_first = prior.first_evidence_at if prior else min(times)
            prior_last = prior.last_evidence_at if prior else max(times)
            item = Interaction(
                id=prior.id if prior else str(uuid4()), chat_id=chat_id,
                message_ids=sorted(ids), topic=local.topic, summary=local.summary,
                participants=sorted(set(local.participants) | (set(prior.participants) if prior else set())),
                first_evidence_at=min(prior_first, min(times)),
                last_evidence_at=max(prior_last, max(times)),
            )
            reserved_ids.add(item.id)
            self.store.save(item)
            result.append(item)
        return MappingResult(interactions=result,
            unassigned_message_ids=draft.unassigned_message_ids,
            unresolved_local_keys=unresolved, diagnostics=diagnostics)
