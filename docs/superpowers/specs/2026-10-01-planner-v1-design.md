# Planner v1 design

## Scope

Graph Manager accepts a task goal, an optional image or observation text, the complete public Skill Library, and an optional GT entity catalog. A model first returns every semantic subgoal as JSON. It then returns one JSON Skill Subgraph per subgoal. Graph Manager parses and checks these proposals. No robot action is executed in this version.

The catalog is an optional input to `PlanningRequest`. If absent, the model prompt contains no entity catalog, and entity references remain ungrounded. If present, the exact catalog is included in both planning prompts, and every `{"ref":"entity_id"}` must identify one listed entity whose types include the Contract input type. The catalog gives IDs and types only, not evaluator truth or object poses. This preserves the same proposal format for later visual grounding.

## JSON interfaces

Subgoals: `{"schema_version":1,"kind":"subgoal_plan","subgoals":[{"id":"sg_1","goal":"..."}]}`. IDs are unique nonempty strings; goals are nonempty. At least one subgoal is required.

Each subgraph: `{"schema_version":1,"kind":"skill_subgraph","subgoal_id":"sg_1","nodes":[{"id":"n1","skill_id":"skill_004","args":{"object":{"ref":"apple"}},"depends_on":[]}]}`. `subgoal_id` names exactly one proposed subgoal. Every proposed subgoal must receive exactly one nonempty subgraph. Node IDs are unique within their graph. Dependencies name local nodes, cannot repeat or name the node itself, and form a DAG. Nodes may reuse a Skill ID.

Object-like Contract inputs use `{"ref":"..."}`. When a catalog is present, the string is an exact catalog ID; otherwise it may be a referring expression and is marked unresolved. `RobotPose2D` and `Vector2` use objects with exact numeric fields; `OptionalVector2` is either `null` or a Vector2 object. Every Contract input key must appear, including `hint_xy` when its value is `null`. Unknown argument keys fail validation. Boolean is not a number.

Entity catalog: `{"entities":[{"id":"apple","types":["MovableObject"]}]}`. Entity IDs are unique. Types are from the Library's entity type names. Empty catalog is valid and will reject all object references. Passing no catalog is different from passing an empty catalog.

## Components and boundaries

- `domain`: proposal and catalog data, structured validation errors, and type rules. It has no simulator or provider dependency.
- `application`: two-stage planning, prompt construction, and static validation against the public Library. It does not claim natural-language `requires` or `achieves` have been proven.
- `repository`: load the generated public JSON Library, never executor paths for model prompts.
- `adapters`: a model protocol and an OpenAI-compatible chat adapter for a local vLLM endpoint; the same application protocol can later be implemented by DeepSeek Harness. Image bytes are sent as a data URL.
- `controller`: CLI that reads a goal, optional image/observation/catalog, invokes the planner, and saves the proposal plus validation report as JSON.

The model adapter returns text; the application parses JSON and reports path-addressed errors. Invalid model output is saved for inspection and is never treated as executable. The first version does not retry or repair proposals automatically. Static validation cannot prove that a grasp, route, transition, or final task goal will succeed. An execution Runner and online Verifiers will use this interface in a later increment.

## Acceptance

- A fake model demonstrates all subgoals followed by one graph per subgoal, using the nine existing Skill IDs.
- Prompt tests prove entity catalog text appears only when supplied.
- Validation tests cover malformed JSON, duplicate/unknown IDs, wrong arguments, wrong or unresolved refs, type mismatch, dangling dependencies, and a cycle.
- A local fake HTTP server proves the vLLM-compatible adapter sends text and image content and reads JSON text responses.
- The repository has an isolated `.venv` setup path, package metadata, and documented test/CLI commands.
