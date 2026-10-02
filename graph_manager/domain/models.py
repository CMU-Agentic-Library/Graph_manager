"""Provider-independent inputs and error records for planning."""

from dataclasses import dataclass
from typing import Literal

ENTITY_TYPES = frozenset(
    {"ArticulatedPart", "MovableObject", "ContainerObject", "SupportSurface", "Microwave"}
)


@dataclass(frozen=True)
class Entity:
    id: str
    types: tuple[str, ...]


@dataclass(frozen=True)
class EntityCatalog:
    entities: tuple[Entity, ...]

    @classmethod
    def from_json(cls, data: object) -> "EntityCatalog":
        if not isinstance(data, dict) or set(data) != {"entities"}:
            raise ValueError("entity catalog must have only an entities array")
        raw_entities = data["entities"]
        if not isinstance(raw_entities, list):
            raise ValueError("entities must be an array")
        entities = []
        seen = set()
        for index, item in enumerate(raw_entities):
            if not isinstance(item, dict) or set(item) != {"id", "types"}:
                raise ValueError(f"entities[{index}] must have id and types")
            entity_id = item["id"]
            types = item["types"]
            if not isinstance(entity_id, str) or not entity_id.strip():
                raise ValueError(f"entities[{index}].id must be a nonempty string")
            if entity_id in seen:
                raise ValueError(f"duplicate entity ID: {entity_id}")
            if (
                not isinstance(types, list)
                or not types
                or any(not isinstance(t, str) or not t.strip() for t in types)
                or len(set(types)) != len(types)
            ):
                raise ValueError(f"entities[{index}].types must be distinct nonempty strings")
            unknown_types = set(types) - ENTITY_TYPES
            if unknown_types:
                raise ValueError(
                    f"unknown entity type in entities[{index}]: {sorted(unknown_types)}"
                )
            entities.append(Entity(entity_id, tuple(types)))
            seen.add(entity_id)
        return cls(tuple(entities))

    def to_json(self) -> dict:
        return {
            "entities": [{"id": entity.id, "types": list(entity.types)} for entity in self.entities]
        }

    def find(self, entity_id: str) -> Entity | None:
        return next((entity for entity in self.entities if entity.id == entity_id), None)


@dataclass(frozen=True)
class StateFact:
    predicate: str
    args: tuple[tuple[str, str], ...]
    value: bool


@dataclass(frozen=True)
class ObservedState:
    """Only facts an observer has explicitly established; absence means unknown."""

    facts: tuple[StateFact, ...]

    @classmethod
    def from_json(cls, data: object) -> "ObservedState":
        if not isinstance(data, dict) or set(data) != {"facts"}:
            raise ValueError("observed state must have only a facts array")
        raw_facts = data["facts"]
        if not isinstance(raw_facts, list):
            raise ValueError("facts must be an array")
        facts = []
        seen = set()
        for index, raw in enumerate(raw_facts):
            if not isinstance(raw, dict) or set(raw) != {"predicate", "args", "value"}:
                raise ValueError(f"facts[{index}] must have predicate, args, and value")
            predicate, args, value = raw["predicate"], raw["args"], raw["value"]
            if not isinstance(predicate, str) or not predicate.strip():
                raise ValueError(f"facts[{index}].predicate must be nonempty")
            if not isinstance(args, dict) or any(
                not isinstance(key, str)
                or not key.strip()
                or not isinstance(arg, str)
                or not arg.strip()
                for key, arg in args.items()
            ):
                raise ValueError(f"facts[{index}].args must map names to nonempty strings")
            if not isinstance(value, bool):
                raise ValueError(f"facts[{index}].value must be boolean")
            key = (predicate, tuple(sorted(args.items())))
            if key in seen:
                raise ValueError(f"duplicate observed fact: {predicate} {args}")
            seen.add(key)
            facts.append(StateFact(predicate, key[1], value))
        return cls(tuple(facts))

    def to_json(self) -> dict:
        return {
            "facts": [
                {"predicate": fact.predicate, "args": dict(fact.args), "value": fact.value}
                for fact in self.facts
            ]
        }

    def find(self, predicate: str, args: dict[str, str]) -> bool | None:
        key = tuple(sorted(args.items()))
        return next(
            (fact.value for fact in self.facts if fact.predicate == predicate and fact.args == key),
            None,
        )


@dataclass(frozen=True)
class PlanningRequest:
    goal: str
    image: bytes | None = None
    image_mime: str = "image/jpeg"
    observation: str | None = None
    entity_catalog: EntityCatalog | None = None
    state: ObservedState | None = None

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise ValueError("goal must be nonempty")
        if self.image is not None and not self.image:
            raise ValueError("image must be nonempty when provided")
        if self.image is not None and self.image_mime not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            raise ValueError("image_mime must be image/jpeg, image/png, or image/webp")


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    text: str
    image: bytes | None = None
    image_mime: str = "image/jpeg"


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str

    def to_json(self) -> dict:
        return {"path": self.path, "code": self.code, "message": self.message}


class ProposalValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{issue.path}: {issue.message}" for issue in issues))


@dataclass(frozen=True)
class PlanAttempt:
    raw_text: str
    issues: tuple[ValidationIssue, ...]

    def to_json(self) -> dict:
        return {
            "raw_text": self.raw_text,
            "issues": [issue.to_json() for issue in self.issues],
        }


@dataclass(frozen=True)
class PlanningResult:
    task_plan: dict
    attempts: tuple[PlanAttempt, ...]
    grounded: bool

    def to_json(self) -> dict:
        return {
            "schema_version": 1,
            "kind": "planning_result",
            "status": "statically_validated" if self.grounded else "unresolved_references",
            "task_plan": self.task_plan,
            "attempts": [attempt.to_json() for attempt in self.attempts],
        }
