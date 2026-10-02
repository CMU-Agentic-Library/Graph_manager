"""Build the model-facing JSON catalog from authoritative Skill Contracts."""

import json
from pathlib import Path

PUBLIC_FIELDS = (
    "id",
    "name",
    "description",
    "inputs",
    "requires",
    "checkable_requires",
    "achieves",
    "outcomes",
)
REQUIRED_FIELDS = (*PUBLIC_FIELDS, "executor", "verifier")


def _read_json(path):
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _validate_contract(contract, types):
    if not isinstance(contract, dict):
        raise ValueError("Skill Contract must be a JSON object")
    missing = [field for field in REQUIRED_FIELDS if field not in contract]
    if missing:
        raise ValueError(f"{contract.get('id', '<unknown>')}: missing {', '.join(missing)}")
    if not isinstance(contract["id"], str) or not contract["id"]:
        raise ValueError("Skill ID must be a nonempty string")
    for field in ("name", "description"):
        if not isinstance(contract[field], str) or not contract[field]:
            raise ValueError(f"{contract['id']}: {field} must be a nonempty string")
    if not isinstance(contract["inputs"], dict):
        raise ValueError(f"{contract['id']}: inputs must be an object")
    unknown = [type_name for type_name in contract["inputs"].values() if type_name not in types]
    if unknown:
        raise ValueError(f"{contract['id']}: unknown input types {', '.join(map(str, unknown))}")
    for field in ("requires", "achieves"):
        if not isinstance(contract[field], list):
            raise ValueError(f"{contract['id']}: {field} must be an array")
    checks = contract["checkable_requires"]
    if not isinstance(checks, list):
        raise ValueError(f"{contract['id']}: checkable_requires must be an array")
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError(f"{contract['id']}: checkable requirement must be an object")
        if check.get("kind") == "fact":
            if set(check) != {"kind", "predicate", "args"}:
                raise ValueError(f"{contract['id']}: invalid fact requirement fields")
            if not isinstance(check["predicate"], str) or not check["predicate"]:
                raise ValueError(f"{contract['id']}: invalid fact predicate")
            if not isinstance(check["args"], dict) or any(
                not isinstance(name, str)
                or not name
                or not isinstance(input_name, str)
                or input_name not in contract["inputs"]
                or contract["inputs"][input_name] in {"RobotPose2D", "Vector2", "OptionalVector2"}
                for name, input_name in check["args"].items()
            ):
                raise ValueError(f"{contract['id']}: invalid fact input binding")
        elif check.get("kind") == "nonzero_vector":
            if (
                set(check) != {"kind", "input"}
                or not isinstance(check["input"], str)
                or contract["inputs"].get(check["input"]) != "Vector2"
            ):
                raise ValueError(f"{contract['id']}: invalid nonzero vector requirement")
        else:
            raise ValueError(f"{contract['id']}: unknown checkable requirement")
    for field in ("outcomes", "executor", "verifier"):
        if not isinstance(contract[field], dict):
            raise ValueError(f"{contract['id']}: {field} must be an object")


def build(root):
    """Return the complete public library for the JSON contracts in *root*."""
    root = Path(root)
    types = _read_json(root / "types.json")["types"]
    if not isinstance(types, dict):
        raise ValueError("types must be an object")

    source_files = sorted((root / "skills").glob("skill_*.json"))
    if not source_files:
        raise ValueError("No skill contracts found")
    contracts = [_read_json(path) for path in source_files]
    for contract in contracts:
        _validate_contract(contract, types)

    ids = [contract["id"] for contract in contracts]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate skill ID")

    connections = []
    for contract in contracts:
        for link in contract.get("connections", []):
            targets = link.get("to") if isinstance(link, dict) else None
            if (
                not isinstance(targets, list)
                or not targets
                or any(target not in ids for target in targets)
            ):
                raise ValueError(f"{contract['id']}: unknown connection target")
            if not isinstance(link.get("when"), str):
                raise ValueError(f"{contract['id']}: connection when must be a string")
            connections.append({"from": contract["id"], "to": targets, "when": link["when"]})

    skills = [{field: contract[field] for field in PUBLIC_FIELDS} for contract in contracts]
    return {
        "version": 1,
        "description": (
            "Complete model-facing ZenoBench Skill Library. Each task-level skill has "
            "one authoritative source contract under skills/."
        ),
        "types": types,
        "skills": skills,
        "connections": connections,
    }


def write_library(root):
    root = Path(root)
    destination = root / "skill_library.json"
    destination.write_text(
        json.dumps(build(root), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return destination


if __name__ == "__main__":
    write_library(Path(__file__).resolve().parent)
