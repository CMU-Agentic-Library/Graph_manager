"""Build model-visible planning turns independently of the model transport."""

from dataclasses import dataclass

from ..domain.models import ImageInput, PlanningRequest, ValidationIssue
from ..prompts.task_plan import SYSTEM_INSTRUCTION, initial_context, validation_feedback


@dataclass(frozen=True)
class ModelTurn:
    text: str
    images: tuple[ImageInput, ...] = ()


class PlanningInputBuilder:
    def initial(self, request: PlanningRequest) -> ModelTurn:
        images = () if request.image is None else (ImageInput(request.image, request.image_mime),)
        return ModelTurn(SYSTEM_INSTRUCTION + "\n\n" + initial_context(request), images)

    def feedback(self, issues: tuple[ValidationIssue, ...]) -> ModelTurn:
        return ModelTurn(validation_feedback(issues))
