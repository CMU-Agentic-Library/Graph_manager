"""Validate one complete model proposal: Subgoals plus one subgraph each."""

from .json_input import parse_json_object
from .models import ProposalValidationError, ValidationIssue
from .skills import SkillCatalog
from .subgraph import NAME, Add, validate_subgraph

TASK_PLAN_KEYS = {"schema_version", "kind", "subgoals", "subgraphs"}


def _subgoal_ids(subgoals: object, add: Add) -> list[str] | None:
    """Return the Subgoal IDs in order, or None when the list itself is invalid."""
    if not isinstance(subgoals, list) or not subgoals:
        add("$.subgoals", "subgoals", "expected a nonempty array")
        return None
    ids: list[str] = []
    valid = True
    for index, subgoal in enumerate(subgoals):
        path = f"$.subgoals[{index}]"
        if not isinstance(subgoal, dict) or set(subgoal) != {"id", "goal"}:
            add(path, "field_names", "expected exactly ['goal', 'id']")
            valid = False
            continue
        if not isinstance(subgoal["id"], str) or not NAME.fullmatch(subgoal["id"]):
            add(f"{path}.id", "identifier", "must match ^[A-Za-z][A-Za-z0-9_-]*$")
            valid = False
            continue
        if subgoal["id"] in ids:
            add(f"{path}.id", "duplicate_id", f"subgoal id {subgoal['id']} is already used")
            valid = False
            continue
        if not isinstance(subgoal["goal"], str) or not subgoal["goal"].strip():
            add(f"{path}.goal", "string_expected", "expected a nonempty string")
            valid = False
        ids.append(subgoal["id"])
    return ids if valid else None


def validate_task_plan(raw_text: str, catalog: SkillCatalog) -> dict:
    """Return the plan, or raise every issue located in the original JSON document."""
    plan = parse_json_object(raw_text)
    if set(plan) != TASK_PLAN_KEYS:
        raise ProposalValidationError(
            [ValidationIssue("$", "field_names", f"expected exactly {sorted(TASK_PLAN_KEYS)}")]
        )
    issues: list[ValidationIssue] = []

    def add(path: str, code: str, message: str) -> None:
        issues.append(ValidationIssue(path, code, message))

    if plan["schema_version"] != 2:
        add("$.schema_version", "schema_version", "must be 2")
    if plan["kind"] != "task_plan":
        add("$.kind", "kind", "must be task_plan")
    subgoal_ids = _subgoal_ids(plan["subgoals"], add)
    graphs = plan["subgraphs"]
    if not isinstance(graphs, list):
        add("$.subgraphs", "subgraphs", "expected an array")
    else:
        first_index: dict[str, int] = {}
        for index, graph in enumerate(graphs):
            path = f"$.subgraphs[{index}]"
            issues.extend(validate_subgraph(graph, catalog, path))
            subgoal_id = graph.get("subgoal_id") if isinstance(graph, dict) else None
            if subgoal_ids is None or not isinstance(subgoal_id, str):
                continue
            if subgoal_id not in subgoal_ids:
                add(
                    f"{path}.subgoal_id", "unknown_subgoal", f"{subgoal_id} is not a listed subgoal"
                )
            elif subgoal_id in first_index:
                add(
                    f"{path}.subgoal_id",
                    "duplicate_subgraph",
                    f"subgoal {subgoal_id} already has subgraphs[{first_index[subgoal_id]}]",
                )
            else:
                first_index[subgoal_id] = index
        if subgoal_ids is not None:
            for subgoal_id in subgoal_ids:
                if subgoal_id not in first_index:
                    add("$.subgraphs", "missing_subgraph", f"subgoal {subgoal_id} has no subgraph")
    if issues:
        raise ProposalValidationError(issues)
    return plan
