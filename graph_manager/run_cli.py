"""Command-line controller for closed-loop runs against the ZenoBench environment."""

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from .adapters.env_http import HttpEnvironment
from .adapters.zenobench_library import TaskEntry, ZenoBenchLibrary
from .adapters.zenobench_sync import DEFAULT_CHECKOUT, DEFAULT_REPO, pull, sync
from .application.orchestration.batch_runner import BatchConfig, BatchRunner
from .application.orchestration.episode_runner import (
    EpisodeLimits,
    EpisodeResult,
    EpisodeRunner,
)
from .application.orchestration.trajectory import DirectoryRecorder
from .domain.env_types import TaskRequest
from .harness_args import add_harness_arguments, check_patches, open_session
from .summary import write_summary

DIFFICULTIES = ("easy", "medium", "hard")


def seeds(text: str) -> list[int]:
    """One seed (10) or an inclusive range (10-19)."""
    first, _, last = text.partition("-")
    try:
        low, high = int(first), int(last or first)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a seed or a seed range: {text!r}") from None
    if high < low:
        raise argparse.ArgumentTypeError(f"empty seed range: {text!r}")
    return list(range(low, high + 1))


def prepare_library(args) -> Path:
    """Pull the latest ZenoBench and copy its Skill Library into the run directory."""
    commit = pull(args.zenobench_checkout, args.zenobench_repo, args.zenobench_ref)
    check_resume(args.out, commit)
    root = args.out / "zenobench"
    sync(args.zenobench_checkout, root)
    print(f"using ZenoBench {commit}", file=sys.stderr)
    return root


def check_resume(out: Path, commit: str) -> None:
    """A run directory keeps finished tasks, so all of them must use one Skill Library."""
    info_path = out / "run.json"
    if not info_path.is_file():
        return
    previous = json.loads(info_path.read_text()).get("zenobench_commit")
    if previous and previous != commit:
        raise ValueError(
            f"{out} was run with ZenoBench {previous}, but this run would use {commit}; "
            "use a new --out, or --zenobench-root with the earlier copy to resume"
        )


def build_requests(args, tasks: dict[str, TaskEntry]) -> list[TaskRequest]:
    """One request per task and seed; tasks without the asked difficulty are left out."""
    if args.all:
        task_ids = [t.task_id for t in tasks.values() if args.catalog in (None, t.catalog)]
    else:
        task_ids = args.task
    unknown = sorted(set(task_ids) - set(tasks))
    if unknown:
        raise ValueError(f"unknown task IDs: {unknown}")
    if args.variant:
        lacking = sorted(t for t in task_ids if args.variant not in tasks[t].variants)
        if lacking:
            raise ValueError(f"tasks without variant {args.variant!r}: {lacking}")
    if args.difficulty:
        lacking = [t for t in task_ids if args.difficulty not in tasks[t].variants.values()]
        if lacking:
            print(f"skipped, no {args.difficulty} variant: {', '.join(lacking)}", file=sys.stderr)
        task_ids = [t for t in task_ids if t not in lacking]
    if not task_ids:
        raise ValueError("no task to run")
    return [
        TaskRequest(
            task_id,
            profile=args.env_profile or tasks[task_id].default_profile,
            variant=args.variant,
            difficulty=args.difficulty,
            seed=seed,
        )
        for task_id in task_ids
        for seed in sorted({seed for group in args.seed or [[0]] for seed in group})
    ]


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ZenoBench tasks in a closed loop")
    tasks = parser.add_mutually_exclusive_group(required=True)
    tasks.add_argument("--task", action="append", help="task ID; repeatable")
    tasks.add_argument("--all", action="store_true", help="every task, or every task of --catalog")
    parser.add_argument(
        "--catalog",
        choices=("skill_library/tasks.json", "benchmark/v3/tasks.json"),
        help="with --all: only this catalog's tasks",
    )
    parser.add_argument(
        "--env-profile",
        help="a profile the service offers, such as gt, benchmark, or gt_sticky; "
        "default: the task catalog's",
    )
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--variant", help="variant name; default: the service picks by seed")
    choice.add_argument(
        "--difficulty", choices=DIFFICULTIES, help="let the service pick a variant of this tier"
    )
    parser.add_argument(
        "--seed",
        action="append",
        type=seeds,
        help="seed or inclusive range such as 10-19; repeatable (default 0)",
    )
    parser.add_argument("--env-url", help="environment service URL (default: $ZENOBENCH_ENV_URL)")
    parser.add_argument(
        "--out", required=True, type=Path, help="run directory; finished tasks are kept"
    )
    parser.add_argument(
        "--zenobench-root",
        type=Path,
        help="use this synced Skill Library copy, such as graph_manager/vendor/zenobench, "
        "instead of pulling the latest ZenoBench into OUT/zenobench",
    )
    parser.add_argument("--zenobench-repo", default=DEFAULT_REPO, help="ZenoBench git URL to pull")
    parser.add_argument(
        "--zenobench-ref", default="HEAD", help="branch, tag, or commit to pull (default: HEAD)"
    )
    parser.add_argument(
        "--zenobench-checkout",
        type=Path,
        default=DEFAULT_CHECKOUT,
        help=f"local clone used for pulling (default: {DEFAULT_CHECKOUT})",
    )
    add_harness_arguments(parser)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--max-replans", type=int, default=5)
    parser.add_argument("--max-attempts-per-turn", type=int, default=5)
    args = parser.parse_args(argv)

    try:
        env_url = args.env_url or os.getenv("ZENOBENCH_ENV_URL")
        if not env_url:
            raise ValueError("--env-url or ZENOBENCH_ENV_URL is required")
        check_patches(args)
        if args.catalog and not args.all:
            raise ValueError("--catalog needs --all")
        library = ZenoBenchLibrary(args.zenobench_root or prepare_library(args))
        check_resume(args.out, library.commit)
        requests = build_requests(args, library.tasks())
        environment = HttpEnvironment(env_url)
        catalog = library.load()
        meanings = library.predicate_meanings()
        limits = EpisodeLimits(
            max_replans=args.max_replans, max_attempts_per_turn=args.max_attempts_per_turn
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or str(exc)
        print(
            f"could not pull ZenoBench: {detail}\n"
            "use --zenobench-root graph_manager/vendor/zenobench to run with the copy "
            "kept in the repository",
            file=sys.stderr,
        )
        return 2
    except (OSError, ValueError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    def run_episode(request: TaskRequest, attempt_dir: Path) -> EpisodeResult:
        session_id = f"{request.task_id}-{uuid.uuid4().hex[:8]}"
        with open_session(args, library.skills_dir, session_id) as session:
            runner = EpisodeRunner(
                environment,
                session,
                catalog,
                DirectoryRecorder(attempt_dir),
                predicate_meanings=meanings,
                limits=limits,
            )
            return runner.run(request)

    args.out.mkdir(parents=True, exist_ok=True)
    run_info = {
        "zenobench_commit": library.commit,
        "env_url": env_url,
        "provider": args.provider,
        "model": args.model,
        "requests": [request.to_json() for request in requests],
    }
    (args.out / "run.json").write_text(json.dumps(run_info, indent=2) + "\n")
    records = BatchRunner(run_episode, args.out, BatchConfig(concurrency=args.concurrency)).run(
        requests
    )
    summary = write_summary(args.out, ("profile", "difficulty"))
    print(json.dumps(summary["overall"], indent=2))
    return 0 if all(record["status"] != "error" for record in records) else 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
