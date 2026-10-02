# One-shot planning loop design

## Goal

Graph Manager asks a VLM for one complete `task_plan` containing every semantic Subgoal and exactly one Skill Subgraph for each Subgoal. It checks the output, returns a precise list of program-verifiable errors to the same model conversation, and retries a bounded number of times. The accepted plan remains a proposal; robot execution and physical verification are separate future steps.

## Model protocol and conversation

The model receives the task goal, optional image and observation, the complete public Skill Library, and an optional GT entity catalog. A response has this shape:

```json
{
  "schema_version": 1,
  "kind": "task_plan",
  "subgoals": [{"id": "sg_1", "goal": "Hold the apple"}],
  "subgraphs": [{"subgoal_id": "sg_1", "nodes": [{"id": "n1", "skill_id": "skill_004", "args": {"object": {"ref": "apple"}}, "depends_on": []}]}]
}
```

On validation failure, the application appends the raw assistant output and a structured feedback message containing `code`, `path`, and `message` for each proven error. The model sees the original context and this feedback on its next request. A successful response ends the loop; exhaustion produces a rejected run record. The model transport accepts a list of conversation messages rather than a single prompt. The first version has no human pause, but later human feedback can be appended to the same conversation.

## Validation boundary

Pure validators check JSON syntax, shape, unique IDs, complete one-to-one Subgoal/Subgraph coverage, Contract Skill IDs and argument names/types, optional entity catalog IDs/types, dependency references, and acyclicity. Errors point into the submitted task plan with JSON paths. The validator checks machine-readable Contract conditions only when their evidence is available. A nonzero vector input can be checked from the plan itself. Structured state facts, when supplied, can be checked against the initially ready nodes of the first Subgoal. Entity-bound facts additionally require an entity catalog to ground references to exact IDs. Missing facts remain unknown, and later nodes are not checked against the initial scene state. Independent proven precondition failures are reported together; malformed graph structure is reported at the first offending path. Natural-language `requires` remain descriptive and do not yield `precondition_failed` errors by themselves.

## Ownership

- `domain`: request/result types and pure validation.
- `prompts`: initial task-plan instruction and repair feedback formatting.
- `application`: one bounded model/validate/feedback loop and conversation history.
- `adapters`: OpenAI-compatible model transport and public Skill Library JSON loading.
- `cli.py`: file input, dependency construction, and result output.

The application depends on a model protocol, not a concrete endpoint. The CLI and adapters know about files and HTTP. The domain has no I/O. The existing JSON Skill Contracts stay authoritative; a small `checkable_requires` field records only conditions implemented by deterministic validators.
