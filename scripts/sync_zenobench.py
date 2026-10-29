"""Copy the ZenoBench Skill Library files Graph Manager uses, pinned to one commit.

Usage: python scripts/sync_zenobench.py /path/to/ZenoBench

This updates the copy kept in the repository (graph_manager/vendor/zenobench) and the
reference plans used as test data. graph-manager-run does not read that copy unless asked
to: it pulls the latest ZenoBench itself before every run.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from graph_manager.adapters.zenobench_library import DEFAULT_ROOT
from graph_manager.adapters.zenobench_sync import sync

ROOT = Path(__file__).resolve().parents[1]
VENDOR = DEFAULT_ROOT
PLAN_FIXTURES = ROOT / "tests" / "fixtures" / "zenobench_plans"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="local ZenoBench checkout at the commit to pin")
    args = parser.parse_args(argv)
    try:
        commit = sync(args.source.resolve(), VENDOR, PLAN_FIXTURES)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"sync failed: {exc}", file=sys.stderr)
        return 1
    print(f"synced ZenoBench {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
