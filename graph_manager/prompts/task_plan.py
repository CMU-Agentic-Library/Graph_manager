"""Instructions and corrective feedback for one complete schema 2 task plan."""

import json

from ..domain.models import PlanningRequest, ValidationIssue
from ..domain.submission import PLAN_TOOL_NAME

# A task unlike the benchmark tasks, so the example shows the format without an answer.
EXAMPLE_PLAN = {
    "schema_version": 2,
    "kind": "task_plan",
    "subgoals": [{"id": "hold_mug", "goal": "Hold the mug"}],
    "subgraphs": [
        {
            "schema_version": 2,
            "kind": "skill_subgraph",
            "subgoal_id": "hold_mug",
            "nodes": [
                {
                    "id": "n1",
                    "skill": "navigate",
                    "args": {"destination": {"ref": "mug"}},
                    "depends_on": [],
                },
                {
                    "id": "n2",
                    "skill": "pick",
                    "args": {"object": {"ref": "mug"}},
                    "depends_on": ["n1"],
                },
            ],
        }
    ],
}

SYSTEM_INSTRUCTION = (
    "You plan robot tasks with the ZenoBench skills listed in your skill catalog. "
    "Load a skill to read its full instructions before you use it in a plan. "
    f"Submit the plan by calling the {PLAN_TOOL_NAME} tool with the plan object as its "
    "arguments; do not write the plan as text. If the tool rejects the plan, fix every "
    "listed error and call it again. "
    "The plan object has schema_version=2, kind=task_plan, a nonempty subgoals array, "
    "and a subgraphs array. Each subgoal has id and goal. "
    "Give exactly one subgraph per subgoal. Each subgraph has schema_version=2, "
    "kind=skill_subgraph, subgoal_id, and a nonempty nodes array. "
    "A subgoal is one meaningful step toward the task, such as putting one object away, "
    "and may need several nodes; do not make one subgoal per skill call. "
    "Each node has id, skill, args, and depends_on; "
    "depends_on lists only node ids from the same subgraph. "
    "skill is the verb from the skill's signature line, not the catalog name: "
    "the skill fetch-object has the signature fetch(object, receptacle), "
    'so write "skill": "fetch". '
    "Every argument value is an object with exactly one key: "
    '{"ref": scene name} for one scene object or place, {"value": literal} for numbers, '
    "vectors, hands, tags, and lists of scene names (an object_list input is "
    '{"value": ["apple", "orange"]}), or {"from": "<node id>.<output>"} for a measured '
    "output of an earlier node in the same subgraph; list that node in depends_on. "
    "Use scene names exactly as the observation gives them. "
    "Node dependencies must form a DAG.\n\n"
    "Example of the plan object for the task 'hold the mug':\n" + json.dumps(EXAMPLE_PLAN)
)


def initial_context(request: PlanningRequest) -> str:
    sections = ["Task goal:\n" + request.goal]
    if request.observation is not None:
        sections.append("Current observation:\n" + request.observation)
    if request.image is not None:
        sections.append("A current scene image is attached.")
    return "\n\n".join(sections)


def validation_feedback(issues: tuple[ValidationIssue, ...]) -> str:
    return json.dumps(
        {
            "kind": "validation_feedback",
            "accepted": False,
            "errors": [issue.to_json() for issue in issues],
            "instruction": (
                f"Fix these errors and submit the complete task_plan again with {PLAN_TOOL_NAME}."
            ),
        },
        ensure_ascii=False,
    )
