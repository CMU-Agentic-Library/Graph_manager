"""Check a plan against what the robot's hands hold before any of it runs.

subgraph.py checks a plan's form; this check also needs the current observation. Hands are
followed through the plan with each skill's declared hand_empty and holding conditions,
assuming every call succeeds, so only the first conflict is reported: after it the plan
cannot be followed reliably.
"""

import re

from .models import ValidationIssue
from .skills import Condition, SkillCatalog, SkillSpec
from .subgraph import topological_order

HANDS = ("right", "left")
UNKNOWN = "<unknown>"  # a hand whose content comes from a measured output
_INVALIDATED_HOLDING = re.compile(r"^holding\(\s*([^,\s]+)\s*,\s*([^)\s]+)\s*\)$")


def _bound(value: object) -> str | None:
    """The scene name or literal of one argument; None for a measured output."""
    if isinstance(value, dict) and len(value) == 1:
        form, item = next(iter(value.items()))
        if form in ("ref", "value") and isinstance(item, str):
            return item
    return None


def _resolve(arg: str | None, node_args: dict) -> str | None:
    if arg is None or not arg.startswith("$"):
        return arg
    return _bound(node_args.get(arg[1:]))


def _ordered_nodes(plan: dict):
    """(path, node) in execution order: subgoals in order, each subgraph's nodes by depends_on."""
    index_of = {graph["subgoal_id"]: i for i, graph in enumerate(plan["subgraphs"])}
    for subgoal in plan["subgoals"]:
        g = index_of[subgoal["id"]]
        nodes = plan["subgraphs"][g]["nodes"]
        position = {node["id"]: i for i, node in enumerate(nodes)}
        for node in topological_order(nodes):
            yield f"$.subgraphs[{g}].nodes[{position[node['id']]}]", node


def _hand_conditions(conditions: tuple[Condition, ...]) -> list[Condition]:
    return [c for c in conditions if c.name in ("hand_empty", "holding") and not c.negated]


def _origin(source: str) -> str:
    return "it holds it now" if source == "now" else f"node {source} leaves it there"


def hand_issues(plan: dict, catalog: SkillCatalog, robot: dict) -> list[ValidationIssue]:
    """The first call whose hand_empty or holding precondition the plan itself breaks."""
    hands = {"right": robot.get("held_right") or None, "left": robot.get("held_left") or None}
    source = {hand: "now" for hand in HANDS}
    for path, node in _ordered_nodes(plan):
        spec: SkillSpec | None = catalog.resolve(node["skill"])
        if spec is None:
            continue
        args = node["args"]
        call = f"node {node['id']} ({spec.verb})"
        for condition in _hand_conditions(spec.preconditions):
            hand = _resolve(condition.args.get("hand"), args)
            if hand not in HANDS or hands[hand] == UNKNOWN:
                continue
            current = hands[hand]
            if condition.name == "hand_empty" and current is not None:
                message = (
                    f"{call} needs an empty {hand} hand, but the {hand} hand will still hold "
                    f"{current} ({_origin(source[hand])}). Put {current} down before this call, "
                    "for example with place, or plan around it."
                )
                return [ValidationIssue(f"{path}.skill", "hand_not_empty", message)]
            if condition.name == "holding":
                wanted = _resolve(condition.args.get("object"), args)
                if wanted is None or current == wanted:
                    continue
                now = "nothing" if current is None else f"{current} ({_origin(source[hand])})"
                message = (
                    f"{call} needs the {hand} hand to hold {wanted}, but at that point it holds "
                    f"{now}. Pick {wanted} up with the {hand} hand before this call."
                )
                return [ValidationIssue(f"{path}.skill", "hand_not_holding", message)]
        for atom in spec.invalidates:
            match = _INVALIDATED_HOLDING.match(atom)
            if match:
                hand, obj = _resolve(match.group(1), args), _resolve(match.group(2), args)
                if hand in HANDS and (obj is None or hands[hand] in (obj, UNKNOWN)):
                    hands[hand], source[hand] = None, node["id"]
        for condition in _hand_conditions(spec.postconditions):
            hand = _resolve(condition.args.get("hand"), args)
            if hand not in HANDS:
                continue
            if condition.name == "hand_empty":
                hands[hand] = None
            else:
                hands[hand] = _resolve(condition.args.get("object"), args) or UNKNOWN
            source[hand] = node["id"]
    return []
