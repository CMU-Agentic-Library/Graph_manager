"""Read the generated, model-facing Skill Library JSON."""

import json
from pathlib import Path


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
        public_fields = {"id", "name", "description", "inputs", "requires", "achieves", "outcomes"}
        for skill in library["skills"]:
            if not isinstance(skill, dict) or not isinstance(skill.get("inputs"), dict):
                raise ValueError("invalid Skill in public Library")
            private_fields = set(skill) - public_fields
            if private_fields:
                raise ValueError(f"private field in model catalog: {sorted(private_fields)}")
            if not isinstance(skill.get("id"), str) or not skill["id"].strip():
                raise ValueError("invalid Skill ID in public Library")
        ids = [skill["id"] for skill in library["skills"]]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate Skill ID in Library")
        return library
