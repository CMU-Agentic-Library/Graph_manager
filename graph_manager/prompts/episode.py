"""Model-visible text for the closed loop: the task start and the report after each subgoal.

The evaluator's task_status is never included: it would tell the model how close it is
to the answer.
"""

import json
import re
from typing import TYPE_CHECKING

from ..domain.env_types import ContractResult, Observation, TaskInfo
from ..domain.json_input import ONLY_JSON
from ..domain.models import ValidationIssue
from .task_plan import SYSTEM_INSTRUCTION

if TYPE_CHECKING:
    from ..application.execution.graph_executor import GraphRun, NodeRun

ERROR_MEANINGS = {
    "UNKNOWN_CONTRACT": "No skill has this verb; the call was not run.",
    "BAD_CALL": "The call is malformed; it was not run.",
    "INPUT_MISSING": "A required input is missing; the call was not run.",
    "INPUT_UNKNOWN": "An input name or value is not recognized; the call was not run.",
    "NOUN_INVALID": (
        "A scene name does not exist or has the wrong kind for this input; the call was not run."
    ),
    "PRECONDITION_FAILED": (
        "A precondition was false before execution, so the robot did not move and the scene "
        "is unchanged."
    ),
    "NO_PATH": "No execution path fits the given objects in their current state.",
    "POLICY_FAILED": "The motion failed partway; the scene may have changed.",
    "POSTCONDITION_FAILED": "The motion finished, but its intended effect does not hold.",
    "SUBSKILL_FAILED": "One step inside this composite skill failed; see failed_step.",
    "INTERNAL_ERROR": "The simulator raised an error while running the call.",
    "LIMIT_EXCEEDED": "The call or time budget for this task is used up.",
}
RUN_NOTES = {
    "output_missing": (
        "A node reads a measured output that the earlier call did not return, so it was not sent."
    ),
    "no_result": "The environment returned fewer results than calls; the rest did not run.",
}
PREDICATE_NAME = re.compile(r"([a-z_]+)\(")

LOOP_INSTRUCTION = (
    "The robot runs your plan one subgoal at a time. After each subgoal you receive what each "
    "skill call did and a new observation with camera images. Then reply with exactly one JSON "
    "object:\n"
    '- {"kind": "continue"} to run the next planned subgoal unchanged;\n'
    "- a task_plan object for the remaining work only: start with the subgoal that failed, if "
    "one did, and leave out subgoals that already succeeded;\n"
    '- {"kind": "finish"} when the task is complete.\n'
    f"{ONLY_JSON}"
)


def observation_text(observation: Observation) -> str:
    """Objects, robot state, and camera names; never the evaluator's task_status."""
    lines = ["Scene objects (use these exact names in refs):"]
    lines += [f"- {o.name} ({o.kind}) at {list(o.position)}" for o in observation.objects]
    robot = observation.robot
    lines.append(f"Robot base pose [x, y, yaw_deg]: {robot.get('base_pose')}")
    lines.append(
        f"Right hand holds: {robot.get('held_right') or 'nothing'}; "
        f"left hand holds: {robot.get('held_left') or 'nothing'}"
    )
    if observation.images:
        cameras = ", ".join(image.camera for image in observation.images)
        lines.append(f"Attached camera images, in order: {cameras}")
    return "\n".join(lines)


def episode_start_text(task: TaskInfo, observation: Observation) -> str:
    return "\n\n".join(
        [
            SYSTEM_INSTRUCTION,
            LOOP_INSTRUCTION,
            "Task:\n" + task.description,
            "Current observation:\n" + observation_text(observation),
            "Reply now with the complete task_plan.",
        ]
    )


def _false_conditions(result: ContractResult, meanings: dict[str, str]) -> list[dict]:
    reports = []
    for condition in (*result.preconditions, *result.postconditions):
        if condition.get("holds") is not False:
            continue
        atom = str(condition.get("atom"))
        report = {"atom": atom}
        match = PREDICATE_NAME.search(atom)
        if match and meanings.get(match.group(1)):
            report["meaning"] = meanings[match.group(1)]
        reports.append(report)
    return reports


def call_report(node_run: "NodeRun", meanings: dict[str, str]) -> dict:
    result = node_run.result
    report = {
        "node": node_run.node_id,
        "contract": result.contract,
        "args": result.args,
        "success": result.success,
    }
    if result.outputs:
        report["outputs"] = result.outputs
    if not result.success:
        report["error_code"] = result.error_code
        report["meaning"] = ERROR_MEANINGS.get(result.error_code, "See error.")
        report["error"] = result.error
        false_conditions = _false_conditions(result, meanings)
        if false_conditions:
            report["false_conditions"] = false_conditions
        if result.failed_step is not None:
            report["failed_step"] = result.failed_step
    return report


def subgoal_feedback_text(
    subgoal: dict,
    run: "GraphRun",
    observation: Observation,
    meanings: dict[str, str],
    remaining: list[dict],
    continue_blocked: str | None,
) -> str:
    report = {
        "kind": "subgoal_result",
        "subgoal": subgoal,
        "status": "succeeded" if run.succeeded else "failed",
        "calls": [call_report(node_run, meanings) for node_run in run.runs],
    }
    if run.not_run:
        report["not_run"] = list(run.not_run)
    if run.failure in RUN_NOTES:
        report["note"] = RUN_NOTES[run.failure]
    if remaining:
        planned = ", ".join(f"{s['id']} ({s['goal']})" for s in remaining)
        plan_line = f"Remaining planned subgoals: {planned}"
    else:
        plan_line = "No planned subgoals remain."
    if continue_blocked is None:
        ask = (
            'Reply with {"kind": "continue"}, a task_plan for the remaining work, '
            'or {"kind": "finish"}.'
        )
    else:
        ask = (
            f"{continue_blocked} Reply with a task_plan for the remaining work "
            'or {"kind": "finish"}.'
        )
    return "\n\n".join(
        [
            json.dumps(report, ensure_ascii=False),
            "Current observation:\n" + observation_text(observation),
            plan_line,
            ask,
        ]
    )


def decision_feedback(issues: tuple[ValidationIssue, ...]) -> str:
    return json.dumps(
        {
            "kind": "validation_feedback",
            "accepted": False,
            "errors": [issue.to_json() for issue in issues],
            "instruction": (
                'Resubmit one JSON object: {"kind": "continue"}, a task_plan for the remaining '
                'work, or {"kind": "finish"}.'
            ),
        },
        ensure_ascii=False,
    )
