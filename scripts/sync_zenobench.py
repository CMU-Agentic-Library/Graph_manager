"""Copy the ZenoBench Skill Library files Graph Manager uses, pinned to one commit.

Usage: python scripts/sync_zenobench.py /path/to/ZenoBench
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "graph_manager" / "vendor" / "zenobench"
PLAN_FIXTURES = ROOT / "tests" / "fixtures" / "zenobench_plans"


def git(source: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(source), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def sync(source: Path, vendor: Path = VENDOR, fixtures: Path = PLAN_FIXTURES) -> str:
    """Replace vendor and fixtures with the checkout's files; return the pinned commit."""
    library = source / "skill_library"
    if git(source, "status", "--porcelain", "--", "skill_library"):
        raise ValueError("ZenoBench skill_library has uncommitted changes; commit or stash them")
    commit = git(source, "rev-parse", "HEAD")
    skill_dirs = sorted(p for p in (library / "skills").iterdir() if (p / "SKILL.md").is_file())
    if not skill_dirs:
        raise ValueError(f"no skills under {library / 'skills'}")
    for target in (vendor, fixtures):
        if target.exists():
            shutil.rmtree(target)
    for skill_dir in skill_dirs:
        out = vendor / "skills" / skill_dir.name
        out.mkdir(parents=True)
        for name in ("SKILL.md", "skill.json"):
            shutil.copy2(skill_dir / name, out / name)
    shutil.copy2(library / "tasks.json", vendor / "tasks.json")
    fixtures.mkdir(parents=True)
    for plan in sorted((library / "plans").glob("*.skill_subgraph.json")):
        shutil.copy2(plan, fixtures / plan.name)
    (vendor / "COMMIT").write_text(commit + "\n", encoding="utf-8")
    return commit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="local ZenoBench checkout at the commit to pin")
    args = parser.parse_args(argv)
    try:
        commit = sync(args.source.resolve())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"sync failed: {exc}", file=sys.stderr)
        return 1
    print(f"synced ZenoBench {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
