"""Plan with a runtime-owned session while Graph Manager checks proposals."""

from ..domain.models import (
    PlanAttempt,
    PlanningRequest,
    PlanningResult,
    ProposalValidationError,
    ValidationIssue,
)
from ..domain.task_plan_validation import validate_task_plan
from ..ports import ModelPortError, PlanningSessionPort, SkillLibraryPort
from ..prompts.task_plan import SYSTEM_INSTRUCTION, initial_context, validation_feedback
from .errors import PlanningFailure


class HarnessPlanningService:
    def __init__(
        self,
        repository: SkillLibraryPort,
        session: PlanningSessionPort,
        max_attempts: int = 3,
    ):
        if type(max_attempts) is not int or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        self.repository = repository
        self.session = session
        self.max_attempts = max_attempts

    def run(self, request: PlanningRequest) -> PlanningResult:
        library = self.repository.load()
        prompt = SYSTEM_INSTRUCTION + "\n\n" + initial_context(request, library)
        image = request.image
        attempts: list[PlanAttempt] = []
        for attempt_number in range(self.max_attempts):
            try:
                raw_text = self.session.ask(prompt, image, request.image_mime)
            except ModelPortError as exc:
                if exc.partial_output is not None:
                    issue = ValidationIssue("$", "model_output_incomplete", str(exc))
                    attempts.append(PlanAttempt(exc.partial_output, (issue,)))
                    if attempt_number + 1 < self.max_attempts:
                        prompt = validation_feedback((issue,))
                        image = None
                        continue
                else:
                    issue = ValidationIssue("$", "model_error", str(exc))
                raise PlanningFailure((issue,), tuple(attempts)) from exc
            except Exception as exc:
                issue = ValidationIssue("$", "model_error", str(exc))
                raise PlanningFailure((issue,), tuple(attempts)) from exc
            try:
                plan = validate_task_plan(raw_text, library, request.entity_catalog, request.state)
            except ProposalValidationError as exc:
                attempts.append(PlanAttempt(raw_text, exc.issues))
                if attempt_number + 1 == self.max_attempts:
                    raise PlanningFailure(exc.issues, tuple(attempts)) from exc
                prompt = validation_feedback(exc.issues)
                image = None
                continue
            attempts.append(PlanAttempt(raw_text, ()))
            return PlanningResult(plan, tuple(attempts), request.entity_catalog is not None)
        raise AssertionError("positive max_attempts guarantees a return or raise")
