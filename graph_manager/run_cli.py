"""Command-line controller for closed-loop runs against the ZenoBench environment."""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from .adapters.env_http import HttpEnvironment
from .adapters.zenobench_library import DEFAULT_ROOT, ZenoBenchLibrary
from .application.orchestration.batch_runner import BatchConfig, BatchRunner
from .application.orchestration.episode_runner import (
    EpisodeLimits,
    EpisodeResult,
    EpisodeRunner,
)
from .application.orchestration.trajectory import DirectoryRecorder
from .harness_args import add_harness_arguments, check_patches, open_session


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ZenoBench tasks in a closed loop")
    tasks = parser.add_mutually_exclusive_group(required=True)
    tasks.add_argument("--task", action="append", help="task ID from tasks.json; repeatable")
    tasks.add_argument("--all", action="store_true", help="every task in tasks.json")
    parser.add_argument("--env-url", help="environment service URL (default: $ZENOBENCH_ENV_URL)")
    parser.add_argument(
        "--out", required=True, type=Path, help="run directory; finished tasks are kept"
    )
    parser.add_argument("--zenobench-root", type=Path, default=DEFAULT_ROOT)
    add_harness_arguments(parser)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--max-replans", type=int, default=5)
    parser.add_argument("--max-attempts-per-turn", type=int, default=3)
    args = parser.parse_args(argv)

    try:
        env_url = args.env_url or os.getenv("ZENOBENCH_ENV_URL")
        if not env_url:
            raise ValueError("--env-url or ZENOBENCH_ENV_URL is required")
        check_patches(args)
        library = ZenoBenchLibrary(args.zenobench_root)
        known = library.task_ids()
        task_ids = list(known) if args.all else args.task
        unknown = sorted(set(task_ids) - set(known))
        if unknown:
            raise ValueError(f"unknown task IDs: {unknown}")
        environment = HttpEnvironment(env_url)
        catalog = library.load()
        meanings = library.predicate_meanings()
        limits = EpisodeLimits(
            max_replans=args.max_replans, max_attempts_per_turn=args.max_attempts_per_turn
        )
    except (OSError, ValueError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    def run_episode(task_id: str, attempt_dir: Path) -> EpisodeResult:
        session_id = f"{task_id}-{uuid.uuid4().hex[:8]}"
        with open_session(args, library.skills_dir, session_id) as session:
            runner = EpisodeRunner(
                environment,
                session,
                catalog,
                DirectoryRecorder(attempt_dir),
                predicate_meanings=meanings,
                limits=limits,
            )
            return runner.run(task_id)

    args.out.mkdir(parents=True, exist_ok=True)
    run_info = {
        "zenobench_commit": library.commit,
        "env_url": env_url,
        "provider": args.provider,
        "model": args.model,
        "tasks": task_ids,
    }
    (args.out / "run.json").write_text(json.dumps(run_info, indent=2) + "\n")
    summary = BatchRunner(run_episode, args.out, BatchConfig(concurrency=args.concurrency)).run(
        task_ids
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["error"] == 0 else 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
