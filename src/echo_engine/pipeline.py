from __future__ import annotations
from typing import Sequence
from .mapper import SemanticMapper
from .models import Message, MappingResult
from .resolver import InteractionResolver


class MappingPipeline:
    def __init__(self, mapper: SemanticMapper, resolver: InteractionResolver) -> None:
        self.mapper = mapper
        self.resolver = resolver

    def run(self, messages: Sequence[Message]) -> MappingResult:
        return self.resolver.resolve(messages, self.mapper.map(messages))
