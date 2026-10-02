"""Small interfaces used by the planning application."""

from typing import Protocol

from .domain.models import ChatMessage


class ModelPort(Protocol):
    def generate(self, messages: tuple[ChatMessage, ...]) -> str: ...


class SkillLibraryPort(Protocol):
    def load(self) -> dict: ...


class ModelPortError(RuntimeError):
    """A model request failed; a partial output may be repairable."""

    def __init__(self, message: str, partial_output: str | None = None):
        self.partial_output = partial_output
        super().__init__(message)
