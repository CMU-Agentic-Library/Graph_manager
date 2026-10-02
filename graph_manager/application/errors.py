"""Shared failures for planning services."""

from ..domain.models import PlanAttempt, ValidationIssue


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
