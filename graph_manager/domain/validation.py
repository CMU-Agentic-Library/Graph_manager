"""Static checks for versioned model proposals against public Skill Contracts."""

import json
import math
from collections import deque

from .models import ENTITY_TYPES, EntityCatalog, ProposalValidationError, ValidationIssue

RECORD_TYPES = {
    "RobotPose2D": ("x", "y", "yaw_deg"),
    "Vector2": ("x", "y"),
    "OptionalVector2": ("x", "y"),
}


def _fail(path: str, code: str, message: str) -> None:
    raise ProposalValidationError([ValidationIssue(path, code, message)])


def parse_json_object(raw_text: str) -> dict:
    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise ValueError(f"nonfinite JSON number: {token}")

    try:
        value = json.loads(
            raw_text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        _fail("$", "json_syntax", str(exc))
    if not isinstance(value, dict):
        _fail("$", "object_expected", "proposal must be a JSON object")
    return value


def _keys(value: object, expected: set[str], path: str) -> dict:
    if not isinstance(value, dict):
        _fail(path, "object_expected", "expected an object")
    if set(value) != expected:
        _fail(path, "field_names", f"expected exactly {sorted(expected)}")
    return value


def _nonempty_string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "string_expected", "expected a nonempty string")
    return value


def validate_envelope(value: dict, kind: str, expected: set[str]) -> None:
    _keys(value, expected, "$")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        _fail("$.schema_version", "schema_version", "expected schema version 1")
    if value["kind"] != kind:
        _fail("$.kind", "kind", f"expected {kind}")


def validate_subgoal_plan(raw_text: str) -> dict:
    """Parse the first model output; return its JSON form or path-addressed errors."""
    plan = parse_json_object(raw_text)
    validate_envelope(plan, "subgoal_plan", {"schema_version", "kind", "subgoals"})
    validate_subgoals(plan["subgoals"])
    return plan


def validate_subgoals(subgoals: object) -> None:
    """Validate the shared Subgoal array used by both output protocols."""
    if not isinstance(subgoals, list) or not subgoals:
        _fail("$.subgoals", "subgoals", "expected at least one subgoal")
    seen = set()
    for index, item in enumerate(subgoals):
        path = f"$.subgoals[{index}]"
        _keys(item, {"id", "goal"}, path)
        subgoal_id = _nonempty_string(item["id"], f"{path}.id")
        _nonempty_string(item["goal"], f"{path}.goal")
        if subgoal_id in seen:
            _fail(f"{path}.id", "duplicate_subgoal", f"duplicate subgoal ID {subgoal_id}")
        seen.add(subgoal_id)


def _validate_argument(
    value: object, type_name: str, path: str, catalog: EntityCatalog | None
) -> None:
    if type_name in ENTITY_TYPES:
        ref = _keys(value, {"ref"}, path)["ref"]
        ref = _nonempty_string(ref, f"{path}.ref")
        if catalog is not None:
            entity = catalog.find(ref)
            if entity is None:
                _fail(f"{path}.ref", "unknown_entity", f"entity ID {ref} is not in the catalog")
            if type_name not in entity.types:
                _fail(f"{path}.ref", "entity_type", f"{ref} is not a {type_name}")
        return
    if type_name == "OptionalVector2" and value is None:
        return
    if type_name in RECORD_TYPES:
        fields = set(RECORD_TYPES[type_name])
        if not isinstance(value, dict) or set(value) != fields:
            _fail(path, "argument_type", f"expected {type_name} with fields {sorted(fields)}")
        for field in fields:
            number = value[field]
            if (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or not math.isfinite(number)
            ):
                _fail(f"{path}.{field}", "argument_type", "expected a finite number")
        return
    _fail(path, "unsupported_type", f"no validator for Contract type {type_name}")


def _check_acyclic(nodes: list[dict], path: str) -> None:
    successors = {node["id"]: [] for node in nodes}
    indegree = {node["id"]: len(node["depends_on"]) for node in nodes}
    for node in nodes:
        for predecessor in node["depends_on"]:
            successors[predecessor].append(node["id"])
    ready = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    visited = 0
    while ready:
        node_id = ready.popleft()
        visited += 1
        for successor in successors[node_id]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    if visited != len(nodes):
        _fail(f"{path}.nodes", "dependency_cycle", "node dependencies contain a cycle")


def validate_skill_subgraph(
    raw_text: str, subgoal_ids: set[str], library: dict, catalog: EntityCatalog | None = None
) -> dict:
    """Validate one proposed DAG; no catalog leaves refs unresolved."""
    graph = parse_json_object(raw_text)
    validate_envelope(graph, "skill_subgraph", {"schema_version", "kind", "subgoal_id", "nodes"})
    validate_graph(
        {"subgoal_id": graph["subgoal_id"], "nodes": graph["nodes"]},
        subgoal_ids,
        library,
        catalog,
    )
    return graph


def validate_graph(
    graph: object,
    subgoal_ids: set[str],
    library: dict,
    catalog: EntityCatalog | None = None,
    path: str = "$",
) -> None:
    """Validate one graph body and report paths in its containing document."""
    graph = _keys(graph, {"subgoal_id", "nodes"}, path)
    subgoal_id = _nonempty_string(graph["subgoal_id"], f"{path}.subgoal_id")
    if subgoal_id not in subgoal_ids:
        _fail(f"{path}.subgoal_id", "unknown_subgoal", f"unknown subgoal ID {subgoal_id}")
    skills = {skill["id"]: skill for skill in library["skills"]}
    nodes = graph["nodes"]
    if not isinstance(nodes, list) or not nodes:
        _fail(f"{path}.nodes", "nodes", "expected at least one Skill node")
    seen = set()
    for index, node in enumerate(nodes):
        node_path = f"{path}.nodes[{index}]"
        _keys(node, {"id", "skill_id", "args", "depends_on"}, node_path)
        node_id = _nonempty_string(node["id"], f"{node_path}.id")
        if node_id in seen:
            _fail(f"{node_path}.id", "duplicate_node", f"duplicate node ID {node_id}")
        seen.add(node_id)
        skill_id = _nonempty_string(node["skill_id"], f"{node_path}.skill_id")
        skill = skills.get(skill_id)
        if skill is None:
            _fail(f"{node_path}.skill_id", "unknown_skill", f"unknown Skill ID {skill_id}")
        arguments = node["args"]
        expected_args = skill["inputs"]
        if not isinstance(arguments, dict) or set(arguments) != set(expected_args):
            _fail(
                f"{node_path}.args", "argument_names", f"expected exactly {sorted(expected_args)}"
            )
        for name, type_name in expected_args.items():
            _validate_argument(arguments[name], type_name, f"{node_path}.args.{name}", catalog)
        dependencies = node["depends_on"]
        if not isinstance(dependencies, list):
            _fail(f"{node_path}.depends_on", "dependencies", "expected an array")
        seen_dependencies = set()
        for position, predecessor in enumerate(dependencies):
            if not isinstance(predecessor, str) or not predecessor:
                _fail(
                    f"{node_path}.depends_on[{position}]",
                    "dependency_type",
                    "expected a node ID string",
                )
            if predecessor == node_id:
                _fail(
                    f"{node_path}.depends_on[{position}]",
                    "self_dependency",
                    "node cannot depend on itself",
                )
            if predecessor in seen_dependencies:
                _fail(
                    f"{node_path}.depends_on[{position}]",
                    "duplicate_dependency",
                    f"duplicate predecessor {predecessor}",
                )
            seen_dependencies.add(predecessor)
    for index, node in enumerate(nodes):
        for position, predecessor in enumerate(node["depends_on"]):
            if predecessor not in seen:
                _fail(
                    f"{path}.nodes[{index}].depends_on[{position}]",
                    "unknown_dependency",
                    f"unknown node ID {predecessor}",
                )
    _check_acyclic(nodes, path)


def validate_complete_plan(plan: dict, graphs: list[dict]) -> None:
    """Require exactly one graph for each subgoal in the first proposal."""
    expected = {item["id"] for item in plan["subgoals"]}
    seen = set()
    for index, graph in enumerate(graphs):
        subgoal_id = graph["subgoal_id"]
        if subgoal_id in seen:
            _fail(
                f"$.subgraphs[{index}].subgoal_id",
                "duplicate_subgraph",
                f"more than one graph for {subgoal_id}",
            )
        if subgoal_id not in expected:
            _fail(
                f"$.subgraphs[{index}].subgoal_id",
                "unknown_subgoal",
                f"unknown subgoal ID {subgoal_id}",
            )
        seen.add(subgoal_id)
    missing = expected - seen
    if missing:
        _fail("$.subgraphs", "missing_subgraph", f"missing graph for {sorted(missing)}")
