"""Instructions and corrective feedback for one complete task plan."""

import json

from ..domain.models import PlanningRequest, ValidationIssue

SYSTEM_INSTRUCTION = (
    "You plan robot tasks with the supplied public Skill Library. "
    "Return exactly one JSON object and no markdown. "
    "The object has schema_version=1, kind=task_plan, a nonempty subgoals array, "
    "and a subgraphs array. Each subgoal has id and goal. "
    "Each subgraph has subgoal_id and a nonempty nodes array. "
    "Each node has id, skill_id, args, and depends_on. "
    "There must be exactly one subgraph per subgoal. "
    "Use only Skill IDs and input names from the Library. "
    "Node dependencies refer to node IDs in that subgraph and must form a DAG. "
    "Every Contract input key must appear; OptionalVector2 may be null. "
    "Do not claim that physical preconditions have been verified."
)


def initial_context(request: PlanningRequest, library: dict) -> str:
    sections = [
        "Task goal:\n" + request.goal,
        "Complete public Skill Library JSON:\n" + json.dumps(library, ensure_ascii=False),
    ]
    if request.observation is not None:
        sections.append("Current observation text:\n" + request.observation)
    if request.image is not None:
        sections.append("A current scene image is attached.")
    if request.entity_catalog is not None:
        sections.append(
            "GT entity catalog (use exact IDs in refs):\n"
            + json.dumps(request.entity_catalog.to_json(), ensure_ascii=False)
        )
    else:
        sections.append(
            'Entity IDs are not provided. Use {"ref":"referring expression"} for entity inputs; '
            "these references remain unresolved until grounding."
        )
    if request.state is not None:
        sections.append(
            "Verified current state facts:\n"
            + json.dumps(request.state.to_json(), ensure_ascii=False)
        )
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
