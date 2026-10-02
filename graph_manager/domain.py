"""Provider-independent inputs and error records for planning."""

from dataclasses import dataclass

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
class PlanningRequest:
    goal: str
    image: bytes | None = None
    image_mime: str = "image/jpeg"
    observation: str | None = None
    entity_catalog: EntityCatalog | None = None

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
