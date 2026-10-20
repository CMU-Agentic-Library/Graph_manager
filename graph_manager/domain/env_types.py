"""Data exchanged with the ZenoBench environment service (interface v2)."""

import base64
import binascii
from dataclasses import dataclass

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
class CameraImage:
    camera: str
    png: bytes


@dataclass(frozen=True)
class SceneObject:
    name: str
    kind: str
    position: tuple[float, ...]


@dataclass(frozen=True)
class Observation:
    images: tuple[CameraImage, ...]
    objects: tuple[SceneObject, ...]
    robot: dict
    # Evaluator truth for each goal clause: keep it in logs, never show it to the model.
    task_status: tuple[dict, ...]

    @classmethod
    def from_json(cls, data: object) -> "Observation":
        images = []
        for item in _field(data, "images", list):
            try:
                png = base64.b64decode(_field(item, "png_base64", str), validate=True)
            except binascii.Error as exc:
                raise ValueError(f"invalid png_base64: {exc}") from exc
            images.append(CameraImage(_field(item, "camera", str), png))
        objects = tuple(
            SceneObject(
                _field(o, "name", str), _field(o, "kind", str), tuple(_field(o, "position", list))
            )
            for o in _field(data, "objects", list)
        )
        return cls(
            tuple(images),
            objects,
            _field(data, "robot", dict),
            tuple(_field(data, "task_status", list)),
        )


@dataclass(frozen=True)
class TaskInfo:
    task_id: str
    name: str
    description: str


@dataclass(frozen=True)
class StartedTask:
    exp_id: str
    task: TaskInfo
    observation: Observation

    @classmethod
    def from_json(cls, data: object) -> "StartedTask":
        task = _field(data, "task", dict)
        return cls(
            _field(data, "exp_id", str),
            TaskInfo(
                _field(task, "task_id", str),
                _field(task, "name", str),
                _field(task, "description", str),
            ),
            Observation.from_json(_field(data, "observation", dict)),
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

    @classmethod
    def from_json(cls, data: object) -> "GoalCheck":
        return cls(
            _field(data, "exp_id", str),
            _field(data, "success", bool),
            tuple(_field(data, "goal", list)),
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
