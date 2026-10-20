"""Typed view of ZenoBench skill.json Contracts used for static checks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InputSpec:
    type: str
    required: bool


@dataclass(frozen=True)
class SkillSpec:
    skill_id: str
    verb: str
    inputs: dict[str, InputSpec]
    outputs: dict[str, str]
    name: str = ""

    @classmethod
    def from_json(cls, data: dict) -> "SkillSpec":
        try:
            required = set(data["required_inputs"])
            inputs = {
                name: InputSpec(spec["type"], name in required)
                for name, spec in data["inputs"].items()
            }
            outputs = {name: spec["type"] for name, spec in data["outputs"].items()}
            return cls(data["skill_id"], data["verb"], inputs, outputs, data["name"])
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError(f"invalid skill.json: missing or malformed {exc}") from exc


class SkillCatalog:
    """All skills, addressable by verb (the contract name) or by skill ID."""

    def __init__(self, skills: tuple[SkillSpec, ...]):
        self.skills = skills
        self._by_key: dict[str, SkillSpec] = {}
        for skill in skills:
            for key in (skill.skill_id, skill.verb):
                if key in self._by_key:
                    raise ValueError(f"duplicate skill key: {key}")
                self._by_key[key] = skill
        self._verb_by_name = {skill.name: skill.verb for skill in skills if skill.name}

    def resolve(self, key: str) -> SkillSpec | None:
        return self._by_key.get(key)

    def verb_for_name(self, name: str) -> str | None:
        """The verb of a SKILL.md catalog name, used only to explain an unknown skill."""
        return self._verb_by_name.get(name)
