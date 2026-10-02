"""Command-line entry point for one complete-plan agent loop."""

import argparse
import json
import os
import sys
from pathlib import Path

from .adapters.openai_compatible import OpenAICompatibleModel
from .adapters.skill_library_json import JsonSkillLibraryRepository
from .application.planning_loop import PlanningFailure, PlanningLoop
from .plan_inputs import DEFAULT_LIBRARY, add_request_arguments, read_request


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate a task Skill plan")
    add_request_arguments(parser)
    parser.add_argument(
        "--library", type=Path, default=DEFAULT_LIBRARY, help="generated public Skill Library JSON"
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="OpenAI-compatible endpoint, e.g. http://localhost:8000/v1",
    )
    parser.add_argument("--model", required=True, help="served VLM model name")
    parser.add_argument("--max-attempts", type=int, default=3, help="maximum plan repair attempts")
    parser.add_argument("--output", required=True, type=Path, help="planning result JSON path")
    args = parser.parse_args(argv)
    try:
        request = read_request(args)
        model = OpenAICompatibleModel(
            args.base_url, args.model, api_key=os.getenv("GRAPH_MANAGER_API_KEY")
        )
        service = PlanningLoop(
            JsonSkillLibraryRepository(args.library), model, max_attempts=args.max_attempts
        )
        try:
            result = service.run(request).to_json()
            exit_code = 0
        except PlanningFailure as exc:
            result = exc.to_json()
            exit_code = 1
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
