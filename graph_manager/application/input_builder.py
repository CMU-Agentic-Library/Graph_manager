"""Build model-visible planning turns independently of the model transport."""

from dataclasses import dataclass

from ..domain.models import PlanningRequest, ValidationIssue
from ..prompts.task_plan import SYSTEM_INSTRUCTION, initial_context, validation_feedback


@dataclass(frozen=True)
class ModelTurn:
    text: str
    image: bytes | None = None
    image_mime: str = "image/jpeg"


class PlanningInputBuilder:
    def initial(self, request: PlanningRequest) -> ModelTurn:
        return ModelTurn(
            text=SYSTEM_INSTRUCTION + "\n\n" + initial_context(request),
            image=request.image,
            image_mime=request.image_mime,
        )

    def feedback(self, issues: tuple[ValidationIssue, ...]) -> ModelTurn:
        return ModelTurn(text=validation_feedback(issues))
