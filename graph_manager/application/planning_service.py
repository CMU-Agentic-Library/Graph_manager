"""One application-level planning policy for a session-owned model history."""

from ..domain.models import (
    PlanAttempt,
    PlanningRequest,
    PlanningResult,
    ProposalValidationError,
    ValidationIssue,
)
from ..domain.task_plan import validate_task_plan
from ..ports import ModelPortError, PlanningSessionPort, SkillLibraryPort
from .errors import PlanningFailure
from .input_builder import PlanningInputBuilder


class PlanningService:
    def __init__(
        self,
        repository: SkillLibraryPort,
        session: PlanningSessionPort,
        max_attempts: int = 3,
        input_builder: PlanningInputBuilder | None = None,
    ):
        if type(max_attempts) is not int or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        self.repository = repository
        self.session = session
        self.max_attempts = max_attempts
        self.input_builder = input_builder or PlanningInputBuilder()

    def run(self, request: PlanningRequest) -> PlanningResult:
        catalog = self.repository.load()
        turn = self.input_builder.initial(request)
        attempts: list[PlanAttempt] = []

        for attempt_number in range(self.max_attempts):
            try:
                raw_text = self.session.ask(turn.text, turn.images)
            except ModelPortError as exc:
                issue = ValidationIssue(
                    "$",
                    "model_output_incomplete" if exc.partial_output is not None else "model_error",
                    str(exc),
                )
                if exc.partial_output is not None:
                    attempts.append(PlanAttempt(exc.partial_output, (issue,)))
                    if attempt_number + 1 < self.max_attempts:
                        turn = self.input_builder.feedback((issue,))
                        continue
                raise PlanningFailure((issue,), tuple(attempts)) from exc
            except Exception as exc:
                issue = ValidationIssue("$", "model_error", str(exc))
                raise PlanningFailure((issue,), tuple(attempts)) from exc

            try:
                plan = validate_task_plan(raw_text, catalog)
            except ProposalValidationError as exc:
                attempts.append(PlanAttempt(raw_text, exc.issues))
                if attempt_number + 1 == self.max_attempts:
                    raise PlanningFailure(exc.issues, tuple(attempts)) from exc
                turn = self.input_builder.feedback(exc.issues)
                continue

            attempts.append(PlanAttempt(raw_text, ()))
            return PlanningResult(plan, tuple(attempts))

        raise AssertionError("positive max_attempts guarantees a return or raise")
