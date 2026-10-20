"""Provider-independent planning inputs, results, and error records."""

from dataclasses import dataclass

IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/webp"})


@dataclass(frozen=True)
class ImageInput:
    """One image attached to a model turn."""

    data: bytes
    mime: str = "image/png"

    def __post_init__(self) -> None:
        if not self.data:
            raise ValueError("image data must be nonempty")
        if self.mime not in IMAGE_MIMES:
            raise ValueError("image mime must be image/jpeg, image/png, or image/webp")


@dataclass(frozen=True)
class PlanningRequest:
    goal: str
    image: bytes | None = None
    image_mime: str = "image/jpeg"
    observation: str | None = None

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise ValueError("goal must be nonempty")
        if self.image is not None and not self.image:
            raise ValueError("image must be nonempty when provided")
        if self.image is not None and self.image_mime not in IMAGE_MIMES:
            raise ValueError("image_mime must be image/jpeg, image/png, or image/webp")


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str

    def to_json(self) -> dict:
        return {"path": self.path, "code": self.code, "message": self.message}


class ProposalValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{issue.path}: {issue.message}" for issue in issues))


@dataclass(frozen=True)
class PlanAttempt:
    raw_text: str
    issues: tuple[ValidationIssue, ...]

    def to_json(self) -> dict:
        return {
            "raw_text": self.raw_text,
            "issues": [issue.to_json() for issue in self.issues],
        }


@dataclass(frozen=True)
class PlanningResult:
    task_plan: dict
    attempts: tuple[PlanAttempt, ...]

    def to_json(self) -> dict:
        return {
            "schema_version": 2,
            "kind": "planning_result",
            "status": "statically_validated",
            "task_plan": self.task_plan,
            "attempts": [attempt.to_json() for attempt in self.attempts],
        }
