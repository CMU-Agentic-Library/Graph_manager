"""Small interfaces between planning and external adapters."""

from typing import Protocol


class PlanningSessionPort(Protocol):
    """A runtime that retains conversation history between calls."""

    session_id: str

    def ask(self, text: str, image: bytes | None = None, image_mime: str = "image/jpeg") -> str:
        raise NotImplementedError


class SkillLibraryPort(Protocol):
    def load(self) -> dict:
        raise NotImplementedError


class ModelPortError(RuntimeError):
    """A model request failed; a partial output may be repairable."""

    def __init__(self, message: str, partial_output: str | None = None):
        self.partial_output = partial_output
        super().__init__(message)
