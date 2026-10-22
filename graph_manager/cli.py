"""Command-line controller for one complete-plan Harness session."""

import argparse
import json
import sys
from pathlib import Path

from .adapters.zenobench_library import DEFAULT_ROOT, ZenoBenchLibrary
from .application.errors import PlanningFailure
from .application.planning_service import PlanningService
from .harness_args import add_harness_arguments, check_patches, open_session
from .plan_inputs import add_request_arguments, read_request


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate a task Skill plan")
    add_request_arguments(parser)
    parser.add_argument(
        "--zenobench-root", type=Path, default=DEFAULT_ROOT, help="synced ZenoBench library"
    )
    add_harness_arguments(parser)
    parser.add_argument("--session-id", help="Harness session ID; use a fresh ID per invocation")
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        request = read_request(args)
        check_patches(args)
        library = ZenoBenchLibrary(args.zenobench_root)
        with open_session(args, library.skills_dir, args.session_id) as session:
            service = PlanningService(library, session, args.max_attempts)
            try:
                result = service.run(request).to_json()
                exit_code = 0
            except PlanningFailure as exc:
                result = exc.to_json()
                exit_code = 1
            result["skill_library"] = {"source": "ZenoBench", "commit": library.commit}
            result["runtime"] = {
                "backend": "deepseek_harness",
                "profile": args.profile,
                "session_id": session.session_id,
                "dsh_home": str(session.dsh_home),
            }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"{result['status']}: {args.output}")
        return exit_code
    except (OSError, ValueError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
