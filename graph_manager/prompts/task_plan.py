"""Instructions and corrective feedback for one complete schema 2 task plan."""

import json

from ..domain.json_input import ONLY_JSON
from ..domain.models import PlanningRequest, ValidationIssue

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
    f"Return exactly one JSON object as your final answer. {ONLY_JSON} "
    "The object has schema_version=2, kind=task_plan, a nonempty subgoals array, "
    "and a subgraphs array. Each subgoal has id and goal. "
    "Give exactly one subgraph per subgoal. Each subgraph has schema_version=2, "
    "kind=skill_subgraph, subgoal_id, and a nonempty nodes array. "
    "Each node has id, skill, args, and depends_on. "
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
    "Example of the format for the task 'hold the mug':\n" + json.dumps(EXAMPLE_PLAN)
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
            "instruction": "Revise and resubmit the complete task_plan JSON object.",
        },
        ensure_ascii=False,
    )
