"""How the model hands in answers: two MCP tools whose arguments vLLM constrains.

vLLM started with --tool-strict-level parameter generates tool arguments that match these
JSON Schemas, so a submitted answer is always well-formed JSON with the right field names
and a known skill verb. The validator still checks what a schema cannot express: each
skill's own inputs, references between nodes, and the DAG.
"""

SERVER_NAME = "graph"
PLAN_TOOL = "submit_plan"
DECISION_TOOL = "submit_decision"
# Harness shows MCP tools to the model as mcp__<server>__<tool>.
PLAN_TOOL_NAME = f"mcp__{SERVER_NAME}__{PLAN_TOOL}"
DECISION_TOOL_NAME = f"mcp__{SERVER_NAME}__{DECISION_TOOL}"
USE_SUBMIT_TOOLS = (
    f"Submit your answer by calling {PLAN_TOOL_NAME} or {DECISION_TOOL_NAME}; "
    "do not write it as text."
)

NAME_PATTERN = "^[A-Za-z][A-Za-z0-9_-]*$"
FROM_PATTERN = "^[A-Za-z][A-Za-z0-9_-]*\\.[A-Za-z0-9_]+$"

DECISION_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string", "enum": ["continue", "finish"]}},
    "required": ["kind"],
    "additionalProperties": False,
}


def _one_key(key: str, schema: dict) -> dict:
    return {
        "type": "object",
        "properties": {key: schema},
        "required": [key],
        "additionalProperties": False,
    }


ARGUMENT_SCHEMA = {
    "anyOf": [
        _one_key("ref", {"type": "string", "minLength": 1}),
        _one_key("value", {}),
        _one_key("from", {"type": "string", "pattern": FROM_PATTERN}),
    ]
}


def plan_schema(verbs: list[str]) -> dict:
    """A schema 2 task_plan; each skill's own inputs are left to the validator."""
    name = {"type": "string", "pattern": NAME_PATTERN}
    node = {
        "type": "object",
        "properties": {
            "id": name,
            "skill": {"type": "string", "enum": list(verbs)},
            "args": {"type": "object", "additionalProperties": ARGUMENT_SCHEMA},
            "depends_on": {"type": "array", "items": name},
        },
        "required": ["id", "skill", "args", "depends_on"],
        "additionalProperties": False,
    }
    subgoal = {
        "type": "object",
        "properties": {"id": name, "goal": {"type": "string", "minLength": 1}},
        "required": ["id", "goal"],
        "additionalProperties": False,
    }
    subgraph = {
        "type": "object",
        "properties": {
            "schema_version": {"type": "integer", "enum": [2]},
            "kind": {"type": "string", "enum": ["skill_subgraph"]},
            "subgoal_id": name,
            "nodes": {"type": "array", "minItems": 1, "items": node},
        },
        "required": ["schema_version", "kind", "subgoal_id", "nodes"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "schema_version": {"type": "integer", "enum": [2]},
            "kind": {"type": "string", "enum": ["task_plan"]},
            "subgoals": {"type": "array", "minItems": 1, "items": subgoal},
            "subgraphs": {"type": "array", "items": subgraph},
        },
        "required": ["schema_version", "kind", "subgoals", "subgraphs"],
        "additionalProperties": False,
    }
