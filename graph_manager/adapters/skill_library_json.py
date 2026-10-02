"""Read the generated, model-facing Skill Library JSON."""

import json
from pathlib import Path

from ..domain.models import ENTITY_TYPES


class JsonSkillLibraryRepository:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> dict:
        with self.path.open(encoding="utf-8") as source:
            library = json.load(source)
        if (
            not isinstance(library, dict)
            or library.get("version") != 1
            or not isinstance(library.get("skills"), list)
            or not isinstance(library.get("types"), dict)
        ):
            raise ValueError("expected Skill Library JSON version 1")
        public_top_level = {"version", "description", "types", "skills", "connections"}
        private_top_level = set(library) - public_top_level
        if private_top_level:
            raise ValueError(f"private field in model catalog: {sorted(private_top_level)}")
        public_fields = {
            "id",
            "name",
            "description",
            "inputs",
            "requires",
            "checkable_requires",
            "achieves",
            "outcomes",
        }
        for skill in library["skills"]:
            if not isinstance(skill, dict) or not isinstance(skill.get("inputs"), dict):
                raise ValueError("invalid Skill in public Library")
            private_fields = set(skill) - public_fields
            if private_fields:
                raise ValueError(f"private field in model catalog: {sorted(private_fields)}")
            if not isinstance(skill.get("id"), str) or not skill["id"].strip():
                raise ValueError("invalid Skill ID in public Library")
            checks = skill.get("checkable_requires")
            if not isinstance(checks, list):
                raise ValueError("checkable_requires must be an array in public Library")
            for check in checks:
                if not isinstance(check, dict):
                    raise ValueError("invalid checkable_requires entry")
                if check.get("kind") == "fact":
                    if (
                        set(check) != {"kind", "predicate", "args"}
                        or not isinstance(check["predicate"], str)
                        or not check["predicate"]
                        or not isinstance(check["args"], dict)
                        or any(
                            not isinstance(name, str)
                            or not name
                            or not isinstance(input_name, str)
                            or input_name not in skill["inputs"]
                            or skill["inputs"][input_name] not in ENTITY_TYPES
                            for name, input_name in check["args"].items()
                        )
                    ):
                        raise ValueError("invalid fact in checkable_requires")
                elif check.get("kind") == "nonzero_vector":
                    if (
                        set(check) != {"kind", "input"}
                        or not isinstance(check["input"], str)
                        or skill["inputs"].get(check["input"]) != "Vector2"
                    ):
                        raise ValueError("invalid vector in checkable_requires")
                else:
                    raise ValueError("unknown checkable_requires kind")
        ids = [skill["id"] for skill in library["skills"]]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate Skill ID in Library")
        return library
