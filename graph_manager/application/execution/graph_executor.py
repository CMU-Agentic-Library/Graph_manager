"""Run one validated skill subgraph through the environment, batch by batch."""

from dataclasses import dataclass

from ...domain.env_types import ContractCall, ContractResult, Observation
from ...domain.skills import SkillCatalog
from ...domain.subgraph import topological_order
from ...ports import EnvironmentPort


@dataclass(frozen=True)
class NodeRun:
    node_id: str
    result: ContractResult


@dataclass(frozen=True)
class GraphRun:
    """What happened to one subgraph; failed_node is None when every node succeeded.

    failure is "contract_failed" (the environment reported a failed contract),
    "output_missing" (a `from` output was absent), or "no_result" (the environment
    returned fewer results than calls without a failure).
    """

    runs: tuple[NodeRun, ...]
    not_run: tuple[str, ...]
    failed_node: str | None
    failure: str | None
    observation: Observation | None

    @property
    def succeeded(self) -> bool:
        return self.failed_node is None


def _sources(node: dict) -> set[str]:
    return {form["from"].split(".", 1)[0] for form in node["args"].values() if "from" in form}


def plan_batches(nodes: list[dict]) -> list[list[dict]]:
    """Split nodes into do_contract batches so every `from` output exists before use."""
    batches: list[list[dict]] = []
    current: list[dict] = []
    for node in topological_order(nodes):
        if _sources(node) & {n["id"] for n in current}:
            batches.append(current)
            current = []
        current.append(node)
    if current:
        batches.append(current)
    return batches


def _resolve(args: dict, outputs: dict[str, dict]) -> dict:
    """Unwrap ref and value forms; read `from` forms from earlier outputs (KeyError if absent)."""
    resolved = {}
    for name, form in args.items():
        ((kind, item),) = form.items()
        if kind == "from":
            source, output = item.split(".", 1)
            resolved[name] = outputs[source][output]
        else:
            resolved[name] = item
    return resolved


def _ids(nodes: list[dict]) -> tuple[str, ...]:
    return tuple(n["id"] for n in nodes)


class GraphExecutor:
    def __init__(self, environment: EnvironmentPort, catalog: SkillCatalog):
        self.environment = environment
        self.catalog = catalog

    def run(self, exp_id: str, graph: dict) -> GraphRun:
        batches = plan_batches(graph["nodes"])
        outputs: dict[str, dict] = {}
        runs: list[NodeRun] = []
        observation: Observation | None = None
        for index, batch in enumerate(batches):
            later = [n for b in batches[index + 1 :] for n in b]
            calls = []
            for position, node in enumerate(batch):
                try:
                    args = _resolve(node["args"], outputs)
                except KeyError:
                    return GraphRun(
                        tuple(runs),
                        _ids(batch[position:] + later),
                        node["id"],
                        "output_missing",
                        observation,
                    )
                calls.append(ContractCall(self.catalog.resolve(node["skill"]).verb, args))
            reply = self.environment.do_contract(exp_id, calls)
            observation = reply.observation
            for node, result in zip(batch, reply.results):
                runs.append(NodeRun(node["id"], result))
                outputs[node["id"]] = result.outputs
            done = len(reply.results)
            if done and not reply.results[-1].success:
                return GraphRun(
                    tuple(runs),
                    _ids(batch[done:] + later),
                    batch[done - 1]["id"],
                    "contract_failed",
                    observation,
                )
            if done < len(batch):
                return GraphRun(
                    tuple(runs),
                    _ids(batch[done:] + later),
                    batch[done]["id"],
                    "no_result",
                    observation,
                )
        return GraphRun(tuple(runs), (), None, None, observation)
