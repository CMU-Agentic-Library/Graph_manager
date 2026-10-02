"""Validate one complete proposal and only provable Contract preconditions."""

from .models import EntityCatalog, ObservedState, ProposalValidationError, ValidationIssue
from .validation import (
    parse_json_object,
    validate_complete_plan,
    validate_envelope,
    validate_graph,
    validate_subgoals,
)


def _check_requirement(
    rule: dict,
    node: dict,
    path: str,
    state: ObservedState | None,
    catalog: EntityCatalog | None,
) -> ValidationIssue | None:
    if rule["kind"] == "nonzero_vector":
        name = rule["input"]
        vector = node["args"][name]
        if vector["x"] == 0 and vector["y"] == 0:
            return ValidationIssue(
                f"{path}.args.{name}",
                "precondition_failed",
                f"{name} must have nonzero length",
            )
        return None
    if state is None or (rule["args"] and catalog is None):
        return None
    arguments = {
        argument: node["args"][input_name]["ref"] for argument, input_name in rule["args"].items()
    }
    observed = state.find(rule["predicate"], arguments)
    if observed is False:
        return ValidationIssue(
            path,
            "precondition_failed",
            f"observed {rule['predicate']}({arguments}) is false",
        )
    return None


def validate_task_plan(
    raw_text: str,
    library: dict,
    catalog: EntityCatalog | None = None,
    state: ObservedState | None = None,
) -> dict:
    """Return a complete plan or raise issues located in the original JSON document.

    State facts describe the current scene. They apply only to initially ready nodes
    in the first Subgoal; checking later nodes against the initial scene is unsound.
    """
    plan = parse_json_object(raw_text)
    validate_envelope(plan, "task_plan", {"schema_version", "kind", "subgoals", "subgraphs"})
    validate_subgoals(plan["subgoals"])
    graphs = plan["subgraphs"]
    if not isinstance(graphs, list):
        raise ProposalValidationError(
            [ValidationIssue("$.subgraphs", "subgraphs", "expected an array")]
        )
    subgoal_ids = {subgoal["id"] for subgoal in plan["subgoals"]}
    for index, graph in enumerate(graphs):
        validate_graph(graph, subgoal_ids, library, catalog, path=f"$.subgraphs[{index}]")
    validate_complete_plan(plan, graphs)

    skills = {skill["id"]: skill for skill in library["skills"]}
    first_subgoal = plan["subgoals"][0]["id"]
    issues = []
    for graph_index, graph in enumerate(graphs):
        initially_active = graph["subgoal_id"] == first_subgoal
        for node_index, node in enumerate(graph["nodes"]):
            path = f"$.subgraphs[{graph_index}].nodes[{node_index}]"
            for rule in skills[node["skill_id"]].get("checkable_requires", []):
                # Input-only conditions hold at every planned node. Scene facts
                # are evaluated only for nodes that can run immediately.
                if rule["kind"] == "fact" and (not initially_active or node["depends_on"]):
                    continue
                issue = _check_requirement(rule, node, path, state, catalog)
                if issue is not None:
                    issues.append(issue)
    if issues:
        raise ProposalValidationError(issues)
    return plan
