"""Parse the model's reply after a subgoal: continue, a new plan for the rest, or finish."""

from dataclasses import dataclass

from .json_input import parse_json_object
from .models import ProposalValidationError, ValidationIssue
from .skills import SkillCatalog
from .task_plan import validate_task_plan

DECISION_KINDS = ("continue", "task_plan", "finish")


@dataclass(frozen=True)
class Decision:
    kind: str
    plan: dict | None = None


def _reject(path: str, code: str, message: str) -> ProposalValidationError:
    return ProposalValidationError([ValidationIssue(path, code, message)])


def validate_decision(
    raw_text: str, catalog: SkillCatalog, continue_blocked: str | None = None
) -> Decision:
    """Return the decision; continue_blocked, when set, says why continue is not allowed."""
    data = parse_json_object(raw_text)
    kind = data.get("kind")
    if kind == "task_plan":
        return Decision("task_plan", validate_task_plan(raw_text, catalog))
    if kind not in DECISION_KINDS:
        raise _reject("$.kind", "kind", 'must be "continue", "task_plan", or "finish"')
    if set(data) != {"kind"}:
        raise _reject("$", "field_names", f'a {kind} reply has only the field "kind"')
    if kind == "continue" and continue_blocked is not None:
        raise _reject("$.kind", "continue_not_allowed", continue_blocked)
    return Decision(kind)
