"""Two-stage semantic subgoal and Skill Subgraph planning."""

import json
from dataclasses import dataclass
from typing import Protocol

from .domain import PlanningRequest, ProposalValidationError, ValidationIssue
from .repository import JsonSkillLibraryRepository
from .validation import (
    validate_complete_plan,
    validate_skill_subgraph,
    validate_subgoal_plan,
)


class ModelAdapter(Protocol):
    def generate(
        self, prompt: str, image: bytes | None = None, image_mime: str = "image/jpeg"
    ) -> str: ...


@dataclass(frozen=True)
class PlanningResult:
    subgoal_plan: dict
    subgraphs: tuple[dict, ...]
    raw_outputs: tuple[dict, ...]
    grounded: bool

    def to_json(self) -> dict:
        return {
            "schema_version": 1,
            "kind": "planning_result",
            "status": "statically_validated" if self.grounded else "unresolved_references",
            "subgoal_plan": self.subgoal_plan,
            "subgraphs": list(self.subgraphs),
            "raw_outputs": list(self.raw_outputs),
        }


class PlanningFailure(Exception):
    def __init__(self, stage: str, issues: tuple[ValidationIssue, ...], raw_outputs: list[dict]):
        self.stage = stage
        self.issues = issues
        self.raw_outputs = tuple(raw_outputs)
        super().__init__(f"{stage}: " + "; ".join(str(issue) for issue in issues))

    def to_json(self) -> dict:
        return {
            "schema_version": 1,
            "kind": "planning_result",
            "status": "rejected",
            "stage": self.stage,
            "issues": [issue.to_json() for issue in self.issues],
            "raw_outputs": list(self.raw_outputs),
        }


def _context(request: PlanningRequest, library: dict) -> str:
    sections = [
        "Task goal:\n" + request.goal,
        "Complete public Skill Library JSON:\n" + json.dumps(library, ensure_ascii=False, indent=2),
    ]
    if request.observation is not None:
        sections.append("Current observation text:\n" + request.observation)
    if request.image is not None:
        sections.append("A current scene image is attached to this request.")
    if request.entity_catalog is not None:
        sections.append(
            "GT entity catalog (exact IDs and types; use exact IDs in refs):\n"
            + json.dumps(request.entity_catalog.to_json(), ensure_ascii=False, indent=2)
        )
    return "\n\n".join(sections)


def _subgoal_prompt(context: str) -> str:
    return (
        "Propose all semantic subgoals for this task. Return only a JSON object with "
        "schema_version=1, kind=subgoal_plan, and a nonempty subgoals array. "
        "Each item has a unique id and a goal sentence. Do not generate a Skill graph yet.\n\n"
        + context
    )


def _graph_prompt(context: str, plan: dict, subgoal: dict, has_catalog: bool) -> str:
    ref_instruction = (
        'For entity inputs, use {"ref":"exact_catalog_id"}.'
        if has_catalog
        else (
            'For entity inputs, use {"ref":"referring expression"}; '
            "these references remain unresolved until grounding."
        )
    )
    return (
        "Propose exactly one Skill Subgraph for the target subgoal. Return only a JSON "
        "object with schema_version=1, kind=skill_subgraph, subgoal_id matching the target, "
        "and a nonempty nodes array. Each node has id, skill_id, args, and depends_on. "
        "Use only Skill IDs and input names from the Library. Dependencies are node IDs "
        "within this subgraph and must form a DAG. Include every Contract argument; "
        "OptionalVector2 may be null. " + ref_instruction + "\n\n"
        "All subgoals:\n" + json.dumps(plan, ensure_ascii=False, indent=2) + "\n\n"
        "Target subgoal:\n" + json.dumps(subgoal, ensure_ascii=False, indent=2) + "\n\n" + context
    )


class PlanningService:
    def __init__(self, repository: JsonSkillLibraryRepository, model: ModelAdapter):
        self.repository = repository
        self.model = model

    def plan(self, request: PlanningRequest) -> PlanningResult:
        library = self.repository.load()
        context = _context(request, library)
        raw_outputs = []

        def ask(stage: str, prompt: str) -> str:
            try:
                raw = self.model.generate(prompt, request.image, request.image_mime)
            except Exception as exc:
                partial = getattr(exc, "raw_content", None)
                if isinstance(partial, str):
                    raw_outputs.append({"stage": stage, "text": partial})
                raise PlanningFailure(
                    stage, (ValidationIssue("$", "model_error", str(exc)),), raw_outputs
                ) from exc
            raw_outputs.append({"stage": stage, "text": raw})
            return raw

        raw_plan = ask("subgoals", _subgoal_prompt(context))
        try:
            plan = validate_subgoal_plan(raw_plan)
        except ProposalValidationError as exc:
            raise PlanningFailure("subgoals", exc.issues, raw_outputs) from exc

        subgoal_ids = {subgoal["id"] for subgoal in plan["subgoals"]}
        graphs = []
        for subgoal in plan["subgoals"]:
            target_id = subgoal["id"]
            raw_graph = ask(
                target_id, _graph_prompt(context, plan, subgoal, request.entity_catalog is not None)
            )
            try:
                graph = validate_skill_subgraph(
                    raw_graph, subgoal_ids, library, request.entity_catalog
                )
                if graph["subgoal_id"] != target_id:
                    raise ProposalValidationError(
                        [
                            ValidationIssue(
                                "$.subgoal_id", "wrong_target_subgoal", f"expected {target_id}"
                            )
                        ]
                    )
            except ProposalValidationError as exc:
                raise PlanningFailure(target_id, exc.issues, raw_outputs) from exc
            graphs.append(graph)
        try:
            validate_complete_plan(plan, graphs)
        except ProposalValidationError as exc:
            raise PlanningFailure("complete_plan", exc.issues, raw_outputs) from exc
        return PlanningResult(
            plan, tuple(graphs), tuple(raw_outputs), request.entity_catalog is not None
        )
