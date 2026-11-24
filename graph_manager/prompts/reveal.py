"""Registry facts for the model, behind ZenoBench's ablation switch SHIFT_REVEAL (default off).

    SHIFT_REVEAL=off       nothing added (main results)
    SHIFT_REVEAL=objects   facts about every kind of object observed so far
    SHIFT_REVEAL=full      the same, plus what each known surface is for

The text comes from ZenoBench's baseline/reveal_card.json, vendored by zenobench_sync, so
Graph Manager shows exactly what ZenoBench's own baselines show: kind-level facts only (what a
kind is, its uses, material and size), never instance state, the task's requirements or which
object may stand in for another.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

MODES = ("off", "objects", "full")
CARD = Path(__file__).resolve().parents[1] / "vendor" / "zenobench" / "reveal_card.json"


def mode() -> str:
    value = (os.environ.get("SHIFT_REVEAL") or "off").strip().lower()
    if value not in MODES:
        raise ValueError(f"SHIFT_REVEAL={value!r}: one of {', '.join(MODES)}")
    return value


@lru_cache(maxsize=None)
def card(path: Path = CARD) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is missing: sync ZenoBench (its baseline/reveal_card.json)"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def system_note() -> str:
    current = mode()
    return "" if current == "off" else card()["system_note"][current].strip()


def object_lines(fields: dict) -> list[str]:
    """Facts for each kind among the observed objects; empty when the switch is off."""
    if mode() == "off":
        return []
    kinds = []
    for item in list(fields.get("visible_objects") or ()) + list(
        fields.get("observation_cache") or ()
    ):
        kind = item.get("category")
        if kind and kind not in kinds:
            kinds.append(kind)
    facts = card()["objects"]
    lines = [facts[kind] for kind in sorted(kinds) if facts.get(kind)]
    return ["Object facts (per kind observed):", *lines] if lines else []


def surface_tags(name: str) -> str:
    """What a known surface is for, in mode full; '' otherwise."""
    if mode() != "full":
        return ""
    return card()["surfaces"].get(name, "")
