"""Instructions and corrective feedback for one complete schema 2 task plan."""

import json

from ..domain.models import PlanningRequest, ValidationIssue

SYSTEM_INSTRUCTION = (
    "You plan robot tasks with the ZenoBench skills listed in your skill catalog. "
    "Load a skill to read its full instructions before you use it in a plan. "
    "Return exactly one JSON object and no markdown. "
    "The object has schema_version=2, kind=task_plan, a nonempty subgoals array, "
    "and a subgraphs array. Each subgoal has id and goal. "
    "Give exactly one subgraph per subgoal. Each subgraph has schema_version=2, "
    "kind=skill_subgraph, subgoal_id, and a nonempty nodes array. "
    "Each node has id, skill (the skill's verb, such as pick), args, and depends_on. "
    'Each argument is {"ref": scene name}, {"value": literal}, or '
    '{"from": "<node id>.<output>"} for a measured output of an earlier node in the '
    "same subgraph; list that node in depends_on. "
    "Use scene names exactly as the observation gives them. "
    "Node dependencies must form a DAG."
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
