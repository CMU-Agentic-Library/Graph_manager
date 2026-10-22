"""Data exchanged with the ZenoBench environment service (interface v3)."""

import base64
import binascii
from dataclasses import dataclass
from pathlib import PurePosixPath

EXP_STATES = frozenset({"running", "ready", "released"})


def _field(data: object, key: str, kind: type | tuple[type, ...]):
    if not isinstance(data, dict) or key not in data or not isinstance(data[key], kind):
        raise ValueError(f"environment reply needs {key!r} of type {kind}")
    return data[key]


@dataclass(frozen=True)
class ContractCall:
    contract: str
    args: dict

    def to_json(self) -> dict:
        return {"contract": self.contract, "args": self.args}


@dataclass(frozen=True)
class ContractResult:
    contract: str
    args: dict
    success: bool
    error_code: str | None
    error: str | None
    preconditions: tuple[dict, ...]
    postconditions: tuple[dict, ...]
    outputs: dict
    failed_step: dict | None

    @classmethod
    def from_json(cls, data: object) -> "ContractResult":
        return cls(
            contract=_field(data, "contract", str),
            args=_field(data, "args", dict),
            success=_field(data, "success", bool),
            error_code=data.get("error_code"),
            error=data.get("error"),
            preconditions=tuple(data.get("preconditions") or ()),
            postconditions=tuple(data.get("postconditions") or ()),
            outputs=data.get("outputs") or {},
            failed_step=data.get("failed_step"),
        )


@dataclass(frozen=True)
class TaskRequest:
    """The initial_task request; None leaves the choice to the service.

    Without a variant the service picks one by seed among the graded variants, only those of
    difficulty when it is given.
    """

    task_id: str
    profile: str | None = None
    variant: str | None = None
    difficulty: str | None = None
    seed: int = 0

    def __post_init__(self):
        if not self.task_id.strip():
            raise ValueError("task_id must be nonempty")
        if self.variant is not None and self.difficulty is not None:
            raise ValueError("give a variant or a difficulty, not both")

    def to_json(self) -> dict:
        body = {"task_id": self.task_id, "seed": self.seed}
        for key in ("profile", "variant", "difficulty"):
            if getattr(self, key) is not None:
                body[key] = getattr(self, key)
        return body

    @property
    def path(self) -> PurePosixPath:
        """<task_id>/<profile>/<variant, difficulty-<d>, or any>/seed_<seed>."""
        if self.variant is not None:
            choice = self.variant
        elif self.difficulty is not None:
            choice = f"difficulty-{self.difficulty}"
        else:
            choice = "any"
        profile = self.profile or "catalog-default"
        return PurePosixPath(self.task_id, profile, choice, f"seed_{self.seed}")


@dataclass(frozen=True)
class CameraImage:
    camera: str
    png: bytes


@dataclass(frozen=True)
class Observation:
    """Camera images plus every other top-level field the profile turned on, as sent."""

    images: tuple[CameraImage, ...]
    fields: dict

    @property
    def task_status(self) -> tuple[dict, ...]:
        """Evaluator truth for each goal clause (gt profile only): logs only, never the model."""
        return tuple(self.fields.get("task_status") or ())

    @classmethod
    def from_json(cls, data: object) -> "Observation":
        if not isinstance(data, dict):
            raise ValueError("observation must be an object")
        images = []
        for item in _field(data, "images", list) if "images" in data else ():
            try:
                png = base64.b64decode(_field(item, "png_base64", str), validate=True)
            except binascii.Error as exc:
                raise ValueError(f"invalid png_base64: {exc}") from exc
            images.append(CameraImage(_field(item, "camera", str), png))
        fields = {key: value for key, value in data.items() if key != "images"}
        return cls(tuple(images), fields)


@dataclass(frozen=True)
class Profile:
    """The profile the exp runs with: its name, observation fields, and contract call limit."""

    name: str
    observation: tuple[str, ...]
    max_calls: int

    @classmethod
    def from_json(cls, data: object) -> "Profile":
        observation = _field(data, "observation", list)
        if not all(isinstance(key, str) for key in observation):
            raise ValueError("profile observation must list field names")
        return cls(_field(data, "name", str), tuple(observation), _field(data, "max_calls", int))


@dataclass(frozen=True)
class TaskInfo:
    task_id: str
    name: str
    description: str


@dataclass(frozen=True)
class StartedTask:
    exp_id: str
    task: TaskInfo
    profile: Profile
    observation: Observation

    @classmethod
    def from_json(cls, data: object) -> "StartedTask":
        task = _field(data, "task", dict)
        profile = Profile.from_json(_field(data, "profile", dict))
        raw_observation = _field(data, "observation", dict)
        missing = [key for key in profile.observation if key not in raw_observation]
        if missing:
            raise ValueError(f"observation lacks the profile's fields {missing}")
        return cls(
            _field(data, "exp_id", str),
            TaskInfo(
                _field(task, "task_id", str),
                _field(task, "name", str),
                _field(task, "description", str),
            ),
            profile,
            Observation.from_json(raw_observation),
        )


@dataclass(frozen=True)
class ExecutionReply:
    exp_id: str
    results: tuple[ContractResult, ...]
    observation: Observation

    @classmethod
    def from_json(cls, data: object) -> "ExecutionReply":
        return cls(
            _field(data, "exp_id", str),
            tuple(ContractResult.from_json(r) for r in _field(data, "results", list)),
            Observation.from_json(_field(data, "observation", dict)),
        )


@dataclass(frozen=True)
class GoalCheck:
    exp_id: str
    success: bool
    goal: tuple[dict, ...]
    dropped: tuple
    # Evaluation metadata (variant, seed, hashes); kept as sent for the run records.
    episode: dict

    @classmethod
    def from_json(cls, data: object) -> "GoalCheck":
        return cls(
            _field(data, "exp_id", str),
            _field(data, "success", bool),
            tuple(_field(data, "goal", list)),
            tuple(_field(data, "dropped", list)),
            _field(data, "episode", dict),
        )


@dataclass(frozen=True)
class ExpStatus:
    """Reply of POST /observe; observation is None while a contract is running."""

    exp_id: str
    state: str
    calls_used: int
    observation: Observation | None

    @classmethod
    def from_json(cls, data: object) -> "ExpStatus":
        state = _field(data, "state", str)
        if state not in EXP_STATES:
            raise ValueError(f"unknown exp state {state!r}")
        raw_observation = data.get("observation")
        return cls(
            _field(data, "exp_id", str),
            state,
            _field(data, "calls_used", int),
            None if raw_observation is None else Observation.from_json(raw_observation),
        )
