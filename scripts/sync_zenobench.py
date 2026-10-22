"""Copy the ZenoBench Skill Library files Graph Manager uses, pinned to one commit.

Usage: python scripts/sync_zenobench.py /path/to/ZenoBench

tasks.json here is an index built from the task catalogs: each task's ID, catalog, default
profile, and variant difficulties. Goals, routes, and variant descriptions stay out, because
the benchmark must not show them to the planner.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "graph_manager" / "vendor" / "zenobench"
PLAN_FIXTURES = ROOT / "tests" / "fixtures" / "zenobench_plans"
# catalog -> default profile, as in ZenoBench episode/catalog.py DEFAULT_CATALOGS
CATALOGS = {"skill_library/tasks.json": "gt", "benchmark/v3/tasks.json": "benchmark"}


def git(source: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(source), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def difficulty_of(variant: dict) -> str:
    """As ZenoBench episode/catalog.py: declared, else by the number of conditions."""
    conditions = variant.get("conditions") or ()
    default = "easy" if not conditions else "medium" if len(conditions) == 1 else "hard"
    return variant.get("difficulty", default)


def task_index(source: Path) -> dict:
    tasks = []
    for catalog, profile in CATALOGS.items():
        data = json.loads((source / catalog).read_text(encoding="utf-8"))
        tasks += [
            {
                "task_id": task["task_id"],
                "catalog": catalog,
                "default_profile": profile,
                "variants": {name: difficulty_of(v) for name, v in task["variants"].items()},
            }
            for task in data["tasks"]
        ]
    ids = [task["task_id"] for task in tasks]
    duplicates = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
    if duplicates:
        raise ValueError(f"task IDs appear in more than one catalog: {duplicates}")
    return {"schema_version": 1, "kind": "task_index", "tasks": tasks}


def sync(source: Path, vendor: Path = VENDOR, fixtures: Path = PLAN_FIXTURES) -> str:
    """Replace vendor and fixtures with the checkout's files; return the pinned commit."""
    library = source / "skill_library"
    if git(source, "status", "--porcelain", "--", "skill_library", *CATALOGS):
        raise ValueError("ZenoBench skill_library has uncommitted changes; commit or stash them")
    commit = git(source, "rev-parse", "HEAD")
    index = task_index(source)
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
    (vendor / "tasks.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
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
