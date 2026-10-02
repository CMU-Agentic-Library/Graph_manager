"""One complete plan per model turn, with bounded corrective feedback."""

from ..domain.models import (
    PlanAttempt,
    PlanningRequest,
    PlanningResult,
    ProposalValidationError,
    ValidationIssue,
)
from ..domain.task_plan_validation import validate_task_plan
from ..ports import ModelPort, ModelPortError, SkillLibraryPort
from ..prompts.task_plan import SYSTEM_INSTRUCTION, initial_context, validation_feedback
from .conversation import Conversation


class PlanningFailure(Exception):
    def __init__(self, issues: tuple[ValidationIssue, ...], attempts: tuple[PlanAttempt, ...]):
        self.issues = issues
        self.attempts = attempts
        super().__init__("; ".join(f"{issue.path}: {issue.message}" for issue in issues))

    def to_json(self) -> dict:
        return {
            "schema_version": 1,
            "kind": "planning_result",
            "status": "rejected",
            "issues": [issue.to_json() for issue in self.issues],
            "attempts": [attempt.to_json() for attempt in self.attempts],
        }


class PlanningLoop:
    def __init__(self, repository: SkillLibraryPort, model: ModelPort, max_attempts: int = 3):
        if type(max_attempts) is not int or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        self.repository = repository
        self.model = model
        self.max_attempts = max_attempts

    def run(self, request: PlanningRequest) -> PlanningResult:
        library = self.repository.load()
        conversation = Conversation(
            SYSTEM_INSTRUCTION,
            initial_context(request, library),
            request.image,
            request.image_mime,
        )
        attempts: list[PlanAttempt] = []
        for attempt_number in range(self.max_attempts):
            try:
                raw_text = self.model.generate(conversation.snapshot())
            except ModelPortError as exc:
                if exc.partial_output is not None:
                    issue = ValidationIssue("$", "model_output_incomplete", str(exc))
                    attempts.append(PlanAttempt(exc.partial_output, (issue,)))
                    conversation.add_model_output(exc.partial_output)
                    if attempt_number + 1 < self.max_attempts:
                        conversation.add_feedback(validation_feedback((issue,)))
                        continue
                else:
                    issue = ValidationIssue("$", "model_error", str(exc))
                raise PlanningFailure((issue,), tuple(attempts)) from exc
            except Exception as exc:
                issue = ValidationIssue("$", "model_error", str(exc))
                raise PlanningFailure((issue,), tuple(attempts)) from exc
            conversation.add_model_output(raw_text)
            try:
                task_plan = validate_task_plan(
                    raw_text, library, request.entity_catalog, request.state
                )
            except ProposalValidationError as exc:
                attempts.append(PlanAttempt(raw_text, exc.issues))
                if attempt_number + 1 == self.max_attempts:
                    raise PlanningFailure(exc.issues, tuple(attempts)) from exc
                conversation.add_feedback(validation_feedback(exc.issues))
                continue
            attempts.append(PlanAttempt(raw_text, ()))
            return PlanningResult(task_plan, tuple(attempts), request.entity_catalog is not None)
        raise AssertionError("positive max_attempts guarantees a return or raise")
