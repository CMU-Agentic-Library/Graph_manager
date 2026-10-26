"""Model-visible text for the closed loop: the task start and the report after each subgoal.

The evaluator's task_status is never included: it would tell the model how close it is
to the answer. Coordinates are left out too: skills take scene names, not positions.
"""

import json
import re
from typing import TYPE_CHECKING

from ..domain.env_types import ContractResult, Observation, TaskInfo
from ..domain.models import ValidationIssue
from ..domain.submission import DECISION_TOOL_NAME, PLAN_TOOL_NAME, USE_SUBMIT_TOOLS
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
    "NOT_OBSERVED": (
        "The robot has not seen this object yet, or no object has this name; the call was not "
        "run. Find it first with search or explore, then retry."
    ),
    "NOT_IN_VIEW": (
        "The object to act on is neither in the current view nor in a hand; the call was not "
        "run. Look at it first with look, then retry."
    ),
    "NOT_FOUND": (
        "The object is no longer where it was last seen; the head may have turned. Search for "
        "it again."
    ),
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
    "skill call did and a new observation with camera images. Then answer with one tool "
    "call:\n"
    f'- {DECISION_TOOL_NAME} with {{"kind": "continue"}} to run the next planned subgoal '
    "unchanged; use it whenever the remaining plan still fits;\n"
    f"- {PLAN_TOOL_NAME} with a task_plan for the remaining work only: send a task_plan only "
    "to change the remaining work. Start with the subgoal that failed, if one did, and leave "
    "out subgoals that already succeeded;\n"
    f'- {DECISION_TOOL_NAME} with {{"kind": "finish"}} when the task is complete.\n'
    "An object shown as <unobserved> is one the robot has not seen; it is not a scene name.\n"
    f"{USE_SUBMIT_TOOLS}"
)
# Never shown as text: the evaluator's truth, and last_result (the subgoal report already
# holds every call result).
HIDDEN_FIELDS = frozenset({"task_status", "last_result"})
SHOWN_FIELDS = ("objects", "visible_objects", "observation_cache", "known_places", "robot")


def _where(item: dict) -> str:
    if item.get("last_seen_in"):
        return f"in {item['last_seen_in']}"
    if item.get("last_seen_on"):
        return f"on {item['last_seen_on']}"
    return "place unknown"


def _seen_line(item: dict) -> str:
    """One visible_objects or observation_cache entry: name, category, and where it is."""
    where = "held" if item.get("held") else _where(item)
    return f"- {item.get('name')} ({item.get('category')}), {where}"


def _places_lines(places: dict) -> list[str]:
    """Places grouped by room; rooms first in the order given, then places with no room."""
    rooms = {name: [] for name, place in places.items() if place.get("kind") == "room"}
    elsewhere = []
    for name, place in places.items():
        if place.get("kind") == "room":
            continue
        entry = f"{name} ({place.get('kind')})"
        if place.get("room") in rooms:
            rooms[place["room"]].append(entry)
        else:
            elsewhere.append(entry)
    lines = [
        f"- {room}: {', '.join(entries) or 'nothing listed'}" for room, entries in rooms.items()
    ]
    if elsewhere:
        lines.append(f"- no room given: {', '.join(elsewhere)}")
    return lines


def _robot_lines(robot: dict) -> list[str]:
    lines = []
    if robot.get("room"):
        lines.append(f"Robot is in room: {robot['room']}")
    lines.append(
        f"Right hand holds: {robot.get('held_right') or 'nothing'}; "
        f"left hand holds: {robot.get('held_left') or 'nothing'}"
    )
    if robot.get("temperatures_c"):
        temperatures = ", ".join(f"{k} {v}" for k, v in robot["temperatures_c"].items())
        lines.append(f"Temperatures of foods seen, in degrees C: {temperatures}")
    return lines


def observation_text(observation: Observation) -> str:
    """Every observation field the profile turned on, except evaluator truth and coordinates.

    Fields this module does not know are shown as compact JSON, so a new environment field
    reaches the model without a code change.
    """
    fields = observation.fields
    lines = []
    if "objects" in fields:
        lines.append("Scene objects (use these exact names in refs):")
        lines += [f"- {o.get('name')} ({o.get('kind')})" for o in fields["objects"]]
    if "visible_objects" in fields:
        lines.append("Objects in view now (use these exact names in refs):")
        lines += [_seen_line(o) for o in fields["visible_objects"]] or ["- none"]
    if "observation_cache" in fields:
        in_view = {o.get("name") for o in fields.get("visible_objects") or ()}
        earlier = [o for o in fields["observation_cache"] if o.get("name") not in in_view]
        if earlier:
            lines.append(
                "Objects seen earlier, by where they were last seen (they may have moved since):"
            )
            lines += [_seen_line(o) for o in earlier]
    if fields.get("known_places"):
        lines.append("Known places from the floor plan, by room:")
        lines += _places_lines(fields["known_places"])
    if "robot" in fields:
        lines += _robot_lines(fields["robot"])
    for key, value in fields.items():
        if key not in HIDDEN_FIELDS and key not in SHOWN_FIELDS:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False, separators=(',', ':'))}")
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
            f"Submit the complete task_plan now with {PLAN_TOOL_NAME}.",
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
            f'Call {DECISION_TOOL_NAME} with {{"kind": "continue"}} if the remaining plan still '
            f"fits, {PLAN_TOOL_NAME} with a task_plan only to change the remaining work, or "
            f'{DECISION_TOOL_NAME} with {{"kind": "finish"}}.'
        )
    else:
        ask = (
            f"{continue_blocked} Call {PLAN_TOOL_NAME} with a task_plan for the remaining "
            f'work, or {DECISION_TOOL_NAME} with {{"kind": "finish"}}.'
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
                f'Fix these errors, then call {DECISION_TOOL_NAME} with {{"kind": "continue"}} '
                f'or {{"kind": "finish"}}, or {PLAN_TOOL_NAME} with a task_plan for the '
                "remaining work."
            ),
        },
        ensure_ascii=False,
    )
