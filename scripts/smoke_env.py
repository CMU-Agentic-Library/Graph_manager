"""Check a live ZenoBench environment service without a model.

    python scripts/smoke_env.py --env-url http://HOST:8800 probe
    python scripts/smoke_env.py --env-url http://HOST:8800 run collect_fruits

probe sends /observe for an exp that does not exist: a 404 UNKNOWN_EXP reply proves the
service is reachable and starts no simulator. run starts one simulator, executes the
ZenoBench reference subgraph for the task, calls check_task (which releases the
simulator), and saves the camera images.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graph_manager.adapters.env_http import HttpEnvironment  # noqa: E402
from graph_manager.adapters.zenobench_library import ZenoBenchLibrary  # noqa: E402
from graph_manager.application.execution.graph_executor import GraphExecutor  # noqa: E402
from graph_manager.domain.subgraph import validate_subgraph  # noqa: E402
from graph_manager.ports import EnvironmentPortError  # noqa: E402

PLANS = ROOT / "tests" / "fixtures" / "zenobench_plans"


def probe(environment: HttpEnvironment) -> int:
    try:
        environment.observe("smoke-env-no-such-exp")
    except EnvironmentPortError as exc:
        if exc.error_code == "UNKNOWN_EXP":
            print(f"reachable: {environment.base_url} answered 404 UNKNOWN_EXP")
            return 0
        print(f"not ready: {exc}", file=sys.stderr)
        return 1
    print("unexpected: /observe accepted a made-up exp_id", file=sys.stderr)
    return 1


def save_images(observation, out: Path, step: str) -> None:
    for image in observation.images:
        (out / f"{step}_{image.camera}.png").write_bytes(image.png)


def run(environment: HttpEnvironment, task_id: str, out: Path) -> int:
    graph = json.loads((PLANS / f"{task_id}.skill_subgraph.json").read_text())
    catalog = ZenoBenchLibrary().load()
    issues = validate_subgraph(graph, catalog)
    if issues:
        print(f"reference plan is invalid: {issues}", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)

    print(f"initial_task {task_id} (may take up to 13 minutes) ...")
    started = environment.initial_task(task_id)
    print(f"exp {started.exp_id}: {started.task.description}")
    print("objects:", [o.name for o in started.observation.objects])
    save_images(started.observation, out, "00_initial")

    try:
        result = GraphExecutor(environment, catalog).run(started.exp_id, graph)
    except EnvironmentPortError as exc:
        print(f"execution stopped: {exc}", file=sys.stderr)
        if exc.exp_gone:
            return 1
    else:
        for node_run in result.runs:
            r = node_run.result
            status = "ok" if r.success else f"FAILED {r.error_code}: {r.error}"
            print(f"  {node_run.node_id} {r.contract}({r.args}) -> {status}")
        if not result.succeeded:
            print(f"stopped at {result.failed_node} ({result.failure}); not run: {result.not_run}")
        if result.observation is not None:
            save_images(result.observation, out, "01_after_graph")

    # check_task also releases the simulator, so it runs even after a failed contract.
    check = environment.check_task(started.exp_id)
    print(f"check_task success={check.success}")
    for atom in check.goal:
        print(f"  {atom}")
    print(f"images saved to {out}")
    return 0 if check.success else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a live ZenoBench environment service")
    parser.add_argument("--env-url", required=True, help="for example http://172.26.34.6:8800")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("probe", help="check reachability; starts no simulator")
    run_parser = commands.add_parser("run", help="run one reference plan on a real simulator")
    run_parser.add_argument("task_id")
    run_parser.add_argument("--out", type=Path, default=ROOT / "run" / "smoke-env")
    args = parser.parse_args(argv)

    environment = HttpEnvironment(args.env_url)
    try:
        if args.command == "probe":
            return probe(environment)
        return run(environment, args.task_id, args.out / args.task_id)
    except EnvironmentPortError as exc:
        print(f"environment error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
