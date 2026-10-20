"""Static checks for one ZenoBench schema 2 skill subgraph.

The rules mirror ZenoBench skill_library/graph.py, but every problem is reported
with a JSON path instead of stopping at the first one. Whether a scene name
exists is left to the environment.
"""

import math
import re
from collections.abc import Callable

from .models import ValidationIssue
from .skills import SkillCatalog, SkillSpec

NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
SUBGRAPH_KEYS = {"schema_version", "kind", "subgoal_id", "nodes"}
NODE_KEYS = {"id", "skill", "args", "depends_on"}
ARG_FORMS = {"ref", "value", "from"}
PLACE_LIKE = {"place_ref", "entity_ref", "receptacle_ref"}

Add = Callable[[str, str, str], None]


def _number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def valid_literal(arg_type: str, value: object) -> bool:
    if arg_type in ("number", "positive_number"):
        return _number(value) and (arg_type == "number" or value > 0)
    if arg_type in ("pose2d", "xy", "unit_vec2"):
        n = 3 if arg_type == "pose2d" else 2
        if not (isinstance(value, list) and len(value) == n and all(map(_number, value))):
            return False
        return arg_type != "unit_vec2" or abs(math.hypot(*value) - 1.0) <= 1e-3
    if arg_type == "hand":
        return value in ("right", "left", "both")
    if arg_type == "tag":
        return isinstance(value, str) and bool(value.strip())
    if arg_type == "object_list":
        return isinstance(value, list) and bool(value) and all(isinstance(v, str) for v in value)
    if arg_type == "category_map":
        return isinstance(value, dict) and all(
            isinstance(k, str) and isinstance(v, str) for k, v in value.items()
        )
    return False


def output_fits(output_type: str, input_type: str) -> bool:
    return (
        output_type == input_type
        or (input_type in PLACE_LIKE and output_type.endswith("_ref"))
        or (input_type == "object_ref" and output_type in ("lid_ref", "container_ref"))
    )


def topological_order(nodes: list[dict]) -> list[dict]:
    """Repeatedly take the first node whose dependencies are done (ZenoBench's order)."""
    ordered, done = [], set()
    while len(ordered) < len(nodes):
        ready = next(
            (n for n in nodes if n["id"] not in done and all(d in done for d in n["depends_on"])),
            None,
        )
        if ready is None:
            raise ValueError("depends_on contains a cycle")
        ordered.append(ready)
        done.add(ready["id"])
    return ordered


def _from_reference(value: object) -> str | None:
    if isinstance(value, dict) and set(value) == {"from"}:
        item = value["from"]
        if isinstance(item, str) and "." in item:
            return item
    return None


def _check_args(args: object, spec: SkillSpec, path: str, add: Add) -> None:
    if not isinstance(args, dict):
        add(path, "object_expected", "expected an object of inputs")
        return
    for name in sorted(set(spec.inputs) - set(args)):
        if spec.inputs[name].required:
            add(f"{path}.{name}", "missing_input", f"{spec.verb} requires input {name}")
    for name, value in args.items():
        arg_path = f"{path}.{name}"
        input_spec = spec.inputs.get(name)
        if input_spec is None:
            add(
                arg_path,
                "unknown_input",
                f"{spec.verb} has no input {name}; inputs are {sorted(spec.inputs)}",
            )
            continue
        if not isinstance(value, dict) or len(value) != 1 or next(iter(value)) not in ARG_FORMS:
            add(
                arg_path,
                "arg_form",
                'use exactly one of {"ref": name}, {"value": literal}, {"from": "node.output"}, '
                'for example "object": {"ref": "apple"}',
            )
            continue
        ((form, item),) = value.items()
        is_ref = input_spec.type.endswith("_ref")
        if form == "ref":
            if not is_ref:
                add(arg_path, "ref_not_allowed", f"{input_spec.type} takes a value, not a ref")
            elif not isinstance(item, str) or not item.strip():
                add(arg_path, "invalid_value", "ref must be a nonempty scene name")
        elif form == "value":
            if is_ref:
                if not isinstance(item, str):
                    add(arg_path, "invalid_value", f"{input_spec.type} value must be a scene name")
            elif not valid_literal(input_spec.type, item):
                add(arg_path, "invalid_value", f"invalid {input_spec.type} value {item!r}")
        elif _from_reference(value) is None:
            add(arg_path, "from_syntax", "from must be '<node id>.<output name>'")


def _unknown_skill_message(key: object, catalog: SkillCatalog) -> str:
    verb = catalog.verb_for_name(key) if isinstance(key, str) else None
    if verb is not None:
        return f"{key!r} is a catalog name; write the verb from its signature: {verb!r}"
    return f"unknown skill {key!r}; write the verb from the skill's signature, such as 'pick'"


def validate_subgraph(
    graph: object, catalog: SkillCatalog, path: str = "$"
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    def add(issue_path: str, code: str, message: str) -> None:
        issues.append(ValidationIssue(issue_path, code, message))

    if not isinstance(graph, dict):
        add(path, "object_expected", "expected a skill_subgraph object")
        return issues
    if set(graph) != SUBGRAPH_KEYS:
        add(path, "field_names", f"expected exactly {sorted(SUBGRAPH_KEYS)}")
        return issues
    if graph["schema_version"] != 2:
        add(f"{path}.schema_version", "schema_version", "must be 2")
    if graph["kind"] != "skill_subgraph":
        add(f"{path}.kind", "kind", "must be skill_subgraph")
    if not isinstance(graph["subgoal_id"], str) or not NAME.fullmatch(graph["subgoal_id"]):
        add(f"{path}.subgoal_id", "identifier", "must match ^[A-Za-z][A-Za-z0-9_-]*$")
    nodes = graph["nodes"]
    if not isinstance(nodes, list) or not nodes:
        add(f"{path}.nodes", "nodes", "expected a nonempty array")
        return issues

    specs: dict[str, SkillSpec] = {}
    index_of: dict[str, int] = {}
    for index, node in enumerate(nodes):
        node_path = f"{path}.nodes[{index}]"
        if not isinstance(node, dict) or set(node) != NODE_KEYS:
            add(node_path, "field_names", f"expected exactly {sorted(NODE_KEYS)}")
            continue
        node_id = node["id"]
        if not isinstance(node_id, str) or not NAME.fullmatch(node_id):
            add(f"{node_path}.id", "identifier", "must match ^[A-Za-z][A-Za-z0-9_-]*$")
            continue
        if node_id in index_of:
            add(f"{node_path}.id", "duplicate_id", f"node id {node_id} is already used")
            continue
        index_of[node_id] = index
        spec = catalog.resolve(node["skill"]) if isinstance(node["skill"], str) else None
        if spec is None:
            add(
                f"{node_path}.skill",
                "unknown_skill",
                _unknown_skill_message(node["skill"], catalog),
            )
        else:
            specs[node_id] = spec
            _check_args(node["args"], spec, f"{node_path}.args", add)

    dependencies_ok = len(index_of) == len(nodes)
    for node_id, index in index_of.items():
        deps = nodes[index]["depends_on"]
        deps_path = f"{path}.nodes[{index}].depends_on"
        if (
            not isinstance(deps, list)
            or not all(isinstance(d, str) for d in deps)
            or len(set(deps)) != len(deps)
        ):
            add(deps_path, "depends_on", "expected an array of unique node ids")
            dependencies_ok = False
            continue
        for dep in deps:
            if dep not in index_of or dep == node_id:
                add(deps_path, "bad_dependency", f"{dep!r} is not another node in this subgraph")
                dependencies_ok = False
    if not dependencies_ok:
        return issues
    try:
        ordered = topological_order(nodes)
    except ValueError:
        add(f"{path}.nodes", "cycle", "depends_on contains a cycle")
        return issues

    ancestors: dict[str, set[str]] = {}
    for node in ordered:
        node_id = node["id"]
        ancestors[node_id] = set(node["depends_on"]).union(
            *(ancestors[d] for d in node["depends_on"])
        )
        spec = specs.get(node_id)
        if spec is None or not isinstance(node["args"], dict):
            continue
        for name, value in node["args"].items():
            reference = _from_reference(value)
            if reference is None or name not in spec.inputs:
                continue
            arg_path = f"{path}.nodes[{index_of[node_id]}].args.{name}"
            source, output = reference.split(".", 1)
            if source not in ancestors[node_id]:
                add(
                    arg_path,
                    "from_not_ancestor",
                    f"{source} is not an ancestor of {node_id}; list it in depends_on",
                )
                continue
            source_spec = specs.get(source)
            if source_spec is None:
                continue
            if output not in source_spec.outputs:
                add(
                    arg_path,
                    "unknown_output",
                    f"{source_spec.verb} has no output {output}; "
                    f"outputs are {sorted(source_spec.outputs)}",
                )
                continue
            output_type = source_spec.outputs[output]
            input_type = spec.inputs[name].type
            if not output_fits(output_type, input_type):
                add(
                    arg_path, "output_type", f"output {output_type} does not fit input {input_type}"
                )
    return issues
