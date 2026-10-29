"""Typed view of ZenoBench skill.json Contracts used for static checks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InputSpec:
    type: str
    required: bool


@dataclass(frozen=True)
class Condition:
    """One precondition or postcondition: hand_empty with {"hand": "right"}, and so on.

    An argument value starting with $ names one of the skill's inputs."""

    name: str
    args: dict[str, str]
    negated: bool = False


def _condition(data: dict) -> Condition:
    return Condition(data["name"], dict(data.get("args") or {}), bool(data.get("negated")))


def _on_every_path(paths) -> tuple[Condition, ...]:
    """Extra preconditions that every policy path adds, so they hold whichever path runs."""
    per_path = [
        {c["predicate"]: c for c in path.get("extra_preconditions") or ()} for path in paths
    ]
    if not per_path:
        return ()
    shared = set.intersection(*(set(conditions) for conditions in per_path))
    return tuple(_condition(per_path[0][key]) for key in sorted(shared))


@dataclass(frozen=True)
class SkillSpec:
    skill_id: str
    verb: str
    inputs: dict[str, InputSpec]
    outputs: dict[str, str]
    name: str = ""
    # Checked before every path and verified after it; path-specific conditions are left out.
    preconditions: tuple[Condition, ...] = ()
    postconditions: tuple[Condition, ...] = ()
    invalidates: tuple[str, ...] = ()  # atoms the call may make false, such as holding(right,$object)

    @classmethod
    def from_json(cls, data: dict) -> "SkillSpec":
        try:
            required = set(data["required_inputs"])
            inputs = {
                name: InputSpec(spec["type"], name in required)
                for name, spec in data["inputs"].items()
            }
            outputs = {name: spec["type"] for name, spec in data["outputs"].items()}
            conditions = {
                key: tuple(_condition(c) for c in data.get(key) or ())
                for key in ("preconditions", "postconditions")
            }
            return cls(
                data["skill_id"],
                data["verb"],
                inputs,
                outputs,
                data["name"],
                conditions["preconditions"] + _on_every_path(data.get("policy_paths") or ()),
                conditions["postconditions"],
                tuple(data.get("invalidates") or ()),
            )
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
