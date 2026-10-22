"""Closed loop for one task: plan, run each subgoal, report back, and decide what next."""

import dataclasses
import time
from collections.abc import Callable
from dataclasses import dataclass

from ...domain.decision import Decision, validate_decision
from ...domain.env_types import Observation, StartedTask
from ...domain.models import ImageInput, ProposalValidationError, ValidationIssue
from ...domain.skills import SkillCatalog
from ...domain.task_plan import validate_task_plan
from ...ports import EnvironmentPort, EnvironmentPortError, ModelPortError, PlanningSessionPort
from ...prompts.episode import decision_feedback, episode_start_text, subgoal_feedback_text
from ...prompts.task_plan import validation_feedback
from ..execution.graph_executor import GraphExecutor, GraphRun
from ..input_builder import ModelTurn
from .trajectory import EpisodeRecorder, observation_record

AFTER_FAILURE = (
    "The subgoal failed, so continue is not allowed: replan starting from it, or finish."
)
ALL_DONE = "Every planned subgoal has run, so continue is not allowed: plan more work, or finish."


class _ModelError(Exception):
    """The model call failed without any output; the episode stops asking the model."""


@dataclass(frozen=True)
class EpisodeLimits:
    max_replans: int = 5
    max_attempts_per_turn: int = 5
    max_duration_s: float = 3600  # the environment's wall-clock limit per exp
    finish_reserve_s: float = 180  # call check_task once less than this is left


@dataclass(frozen=True)
class EpisodeResult:
    task_id: str
    exp_id: str
    session_id: str
    status: str  # "success" or "failure", from check_task
    # why check_task was called: model_finished, model_gave_up (every attempt in a turn
    # failed validation), model_error (the model call failed with no output),
    # replan_limit, time_budget, or limit_exceeded
    reason: str
    goal: tuple[dict, ...]
    replans: int
    subgoal_runs: int
    elapsed_s: float

    def to_json(self) -> dict:
        return dataclasses.asdict(self)


def _images(observation: Observation) -> tuple[ImageInput, ...]:
    return tuple(ImageInput(image.png, "image/png") for image in observation.images)


def _pending(plan: dict) -> list[tuple[dict, dict]]:
    graphs = {graph["subgoal_id"]: graph for graph in plan["subgraphs"]}
    return [(subgoal, graphs[subgoal["id"]]) for subgoal in plan["subgoals"]]


def _hit_limit(run: GraphRun) -> bool:
    return bool(run.runs) and run.runs[-1].result.error_code == "LIMIT_EXCEEDED"


class EpisodeRunner:
    def __init__(
        self,
        environment: EnvironmentPort,
        session: PlanningSessionPort,
        catalog: SkillCatalog,
        recorder: EpisodeRecorder,
        *,
        predicate_meanings: dict[str, str] | None = None,
        limits: EpisodeLimits = EpisodeLimits(),
        clock: Callable[[], float] = time.monotonic,
    ):
        self.environment = environment
        self.session = session
        self.catalog = catalog
        self.recorder = recorder
        self.predicate_meanings = predicate_meanings or {}
        self.limits = limits
        self.clock = clock
        self.executor = GraphExecutor(environment, catalog)

    def run(self, task_id: str) -> EpisodeResult:
        started = self.environment.initial_task(task_id)
        self._started_at = self.clock()
        self._replans = 0
        self._subgoal_runs = 0
        self._observation = started.observation
        self.recorder.event(
            "started",
            {
                "task_id": task_id,
                "exp_id": started.exp_id,
                "session_id": self.session.session_id,
                "task": dataclasses.asdict(started.task),
                "observation": observation_record(started.observation),
            },
        )
        self.recorder.images("00_start", started.observation)
        try:
            try:
                reason = self._loop(started)
            except _ModelError:
                reason = "model_error"
            check = self.environment.check_task(started.exp_id)
        except EnvironmentPortError as exc:
            self.recorder.event(
                "environment_error", {"error_code": exc.error_code, "error": str(exc)}
            )
            if not exc.exp_gone:
                self._release(started.exp_id)
            raise
        self.recorder.event("check", {"reason": reason, **dataclasses.asdict(check)})
        return EpisodeResult(
            task_id=task_id,
            exp_id=started.exp_id,
            session_id=self.session.session_id,
            status="success" if check.success else "failure",
            reason=reason,
            goal=check.goal,
            replans=self._replans,
            subgoal_runs=self._subgoal_runs,
            elapsed_s=self.clock() - self._started_at,
        )

    def _loop(self, started: StartedTask) -> str:
        first = ModelTurn(
            episode_start_text(started.task, started.observation), _images(started.observation)
        )
        decision = self._ask(
            first,
            lambda raw: Decision("task_plan", validate_task_plan(raw, self.catalog)),
            validation_feedback,
        )
        if decision is None:
            return "model_gave_up"
        pending = _pending(decision.plan)
        while True:
            if self._out_of_time():
                return "time_budget"
            subgoal, graph = pending[0]
            run = self.executor.run(started.exp_id, graph)
            self._subgoal_runs += 1
            if run.observation is not None:
                self._observation = run.observation
            self._record_run(subgoal, run)
            if _hit_limit(run):
                return "limit_exceeded"
            if run.succeeded:
                pending = pending[1:]
            blocked = AFTER_FAILURE if not run.succeeded else (None if pending else ALL_DONE)
            if self._out_of_time():
                return "time_budget"
            turn = ModelTurn(
                subgoal_feedback_text(
                    subgoal,
                    run,
                    self._observation,
                    self.predicate_meanings,
                    [s for s, _ in pending],
                    blocked,
                ),
                _images(self._observation),
            )
            decision = self._ask(
                turn,
                lambda raw: validate_decision(raw, self.catalog, blocked),
                decision_feedback,
            )
            if decision is None:
                return "model_gave_up"
            if decision.kind == "finish":
                return "model_finished"
            if decision.kind == "task_plan":
                self._replans += 1
                if self._replans > self.limits.max_replans:
                    return "replan_limit"
                pending = _pending(decision.plan)

    def _ask(
        self,
        turn: ModelTurn,
        parse: Callable[[str], Decision],
        feedback: Callable[[tuple[ValidationIssue, ...]], str],
    ) -> Decision | None:
        """Ask until a reply parses, at most max_attempts_per_turn times; None means give up.

        A model error without any output (a ModelPortError without partial output, or any
        other exception from the session) raises _ModelError at once: the Harness adapter
        closes the session when a turn times out, so the same turn cannot be asked again.
        """
        for _ in range(self.limits.max_attempts_per_turn):
            self.recorder.event("model_turn", {"text": turn.text, "images": len(turn.images)})
            try:
                raw_text = self.session.ask(turn.text, turn.images)
            except ModelPortError as exc:
                self.recorder.event(
                    "model_error", {"error": str(exc), "partial_output": exc.partial_output}
                )
                if exc.partial_output is None:
                    raise _ModelError(str(exc)) from exc
                issue = ValidationIssue("$", "model_output_incomplete", str(exc))
                turn = ModelTurn(feedback((issue,)))
                continue
            except Exception as exc:  # the SDK or runtime failed; the session cannot go on
                error = f"{type(exc).__name__}: {exc}"
                self.recorder.event("model_error", {"error": error})
                raise _ModelError(error) from exc
            try:
                decision = parse(raw_text)
            except ProposalValidationError as exc:
                issues = [issue.to_json() for issue in exc.issues]
                self.recorder.event("model_reply", {"raw_text": raw_text, "issues": issues})
                turn = ModelTurn(feedback(exc.issues))
                continue
            self.recorder.event(
                "model_reply", {"raw_text": raw_text, "issues": [], "decision": decision.kind}
            )
            return decision
        return None

    def _record_run(self, subgoal: dict, run: GraphRun) -> None:
        self.recorder.event(
            "subgoal_run",
            {
                "subgoal": subgoal,
                "succeeded": run.succeeded,
                "failed_node": run.failed_node,
                "failure": run.failure,
                "not_run": list(run.not_run),
                "calls": [
                    {"node": node_run.node_id, **dataclasses.asdict(node_run.result)}
                    for node_run in run.runs
                ],
                "observation": observation_record(self._observation),
            },
        )
        self.recorder.images(f"{self._subgoal_runs:02d}_{subgoal['id']}", self._observation)

    def _out_of_time(self) -> bool:
        elapsed = self.clock() - self._started_at
        return elapsed >= self.limits.max_duration_s - self.limits.finish_reserve_s

    def _release(self, exp_id: str) -> None:
        """Best effort: check_task frees the simulator so later tasks do not wait on BUSY."""
        try:
            self.environment.check_task(exp_id)
        except EnvironmentPortError:
            pass
