"""Command-line options for commands that open a DeepSeek Harness session."""

import argparse
import os
from pathlib import Path

from .adapters.deepseek_harness_sdk import DeepSeekHarnessSession


def add_harness_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dsh-home", required=True, type=Path, help="local Harness state directory"
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--provider", default="deepseek-official")
    parser.add_argument("--model", required=True)
    parser.add_argument("--profile", choices=("sdk",), default="sdk")
    parser.add_argument("--patch", action="append", type=Path, default=[], help="profile patch")
    parser.add_argument("--base-url", help="optional DeepSeek-compatible endpoint override")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--turn-timeout-seconds", type=float, default=300)


def check_patches(args: argparse.Namespace) -> None:
    for patch_file in args.patch:
        if not patch_file.is_file():
            raise ValueError(f"Harness patch does not exist: {patch_file}")


def open_session(
    args: argparse.Namespace, skills_dir: Path, session_id: str | None
) -> DeepSeekHarnessSession:
    return DeepSeekHarnessSession(
        dsh_home=args.dsh_home,
        cwd=args.workspace,
        skills_dir=skills_dir,
        model=args.model,
        provider=args.provider,
        profile=args.profile,
        patches=tuple(args.patch),
        base_url=args.base_url,
        api_key=os.getenv("GRAPH_MANAGER_API_KEY"),
        max_tokens=args.max_tokens,
        session_id=session_id,
        turn_timeout_seconds=args.turn_timeout_seconds,
    )
