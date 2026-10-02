"""Separate command for planning with a DeepSeek Harness SDK session."""

import argparse
import json
import os
import sys
from pathlib import Path

from .adapters.deepseek_harness_sdk import DeepSeekHarnessSession
from .adapters.skill_library_json import JsonSkillLibraryRepository
from .application.errors import PlanningFailure
from .application.harness_planning import HarnessPlanningService
from .plan_inputs import DEFAULT_LIBRARY, add_request_arguments, read_request


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan through a persistent DeepSeek Harness session"
    )
    add_request_arguments(parser)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument(
        "--dsh-home", required=True, type=Path, help="local Harness state directory"
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--provider", default="deepseek-official")
    parser.add_argument("--model", required=True)
    parser.add_argument("--profile", choices=("sdk",), default="sdk")
    parser.add_argument("--patch", action="append", type=Path, default=[], help="profile patch")
    parser.add_argument("--base-url", help="optional DeepSeek-compatible endpoint override")
    parser.add_argument("--session-id", help="Harness session ID; use a fresh ID per invocation")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--turn-timeout-seconds", type=float, default=300)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        request = read_request(args)
        for patch_file in args.patch:
            if not patch_file.is_file():
                raise ValueError(f"Harness patch does not exist: {patch_file}")
        with DeepSeekHarnessSession(
            dsh_home=args.dsh_home,
            cwd=args.workspace,
            model=args.model,
            provider=args.provider,
            profile=args.profile,
            patches=tuple(args.patch),
            base_url=args.base_url,
            api_key=os.getenv("GRAPH_MANAGER_API_KEY"),
            max_tokens=args.max_tokens,
            session_id=args.session_id,
            turn_timeout_seconds=args.turn_timeout_seconds,
        ) as session:
            service = HarnessPlanningService(
                JsonSkillLibraryRepository(args.library), session, args.max_attempts
            )
            try:
                result = service.run(request).to_json()
                exit_code = 0
            except PlanningFailure as exc:
                result = exc.to_json()
                exit_code = 1
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
