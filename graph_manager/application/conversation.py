"""One model-visible conversation for an entire planning run."""

from ..domain.models import ChatMessage


class Conversation:
    def __init__(self, system_instruction: str, task_input: str, image: bytes | None, mime: str):
        self._messages = [
            ChatMessage("system", system_instruction),
            ChatMessage("user", task_input, image, mime),
        ]

    def snapshot(self) -> tuple[ChatMessage, ...]:
        return tuple(self._messages)

    def add_model_output(self, raw_text: str) -> None:
        self._messages.append(ChatMessage("assistant", raw_text))

    def add_feedback(self, feedback: str) -> None:
        self._messages.append(ChatMessage("user", feedback))
