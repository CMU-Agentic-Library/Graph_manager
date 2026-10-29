"""Pull ZenoBench and copy the Skill Library files Graph Manager uses, pinned to one commit.

tasks.json in the copy is an index built from the task catalogs: each task's ID, catalog,
default profile, and variant difficulties. Goals, routes, and variant descriptions stay out,
because the benchmark must not show them to the planner.
"""

import json
import shutil
import subprocess
from pathlib import Path

DEFAULT_REPO = "https://github.com/CMU-Agentic-Library/ZenoBench.git"
DEFAULT_CHECKOUT = Path.home() / ".cache" / "graph-manager" / "ZenoBench"
# catalog -> default profile, as in ZenoBench episode/catalog.py DEFAULT_CATALOGS
CATALOGS = {"skill_library/tasks.json": "gt", "benchmark/v3/tasks.json": "benchmark"}


def git(source: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(source), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def pull(checkout: Path, repo: str = DEFAULT_REPO, ref: str = "HEAD") -> str:
    """Clone repo into checkout if needed, then check out the latest ref; return its commit.

    The checkout is left detached at the fetched commit. Local changes that the checkout
    would overwrite make git refuse, so a working clone is never clobbered.
    """
    if not (checkout / ".git").exists():
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--quiet", repo, str(checkout)],
            check=True,
            capture_output=True,
            text=True,
        )
    git(checkout, "fetch", "--quiet", repo, ref)
    git(checkout, "checkout", "--quiet", "--detach", "FETCH_HEAD")
    return git(checkout, "rev-parse", "HEAD")


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


def sync(source: Path, vendor: Path, fixtures: Path | None = None) -> str:
    """Replace vendor (and fixtures, if given) with the checkout's files; return the commit."""
    library = source / "skill_library"
    if git(source, "status", "--porcelain", "--", "skill_library", *CATALOGS):
        raise ValueError("ZenoBench skill_library has uncommitted changes; commit or stash them")
    commit = git(source, "rev-parse", "HEAD")
    index = task_index(source)
    skill_dirs = sorted(p for p in (library / "skills").iterdir() if (p / "SKILL.md").is_file())
    if not skill_dirs:
        raise ValueError(f"no skills under {library / 'skills'}")
    for target in (vendor, fixtures):
        if target is not None and target.exists():
            shutil.rmtree(target)
    for skill_dir in skill_dirs:
        out = vendor / "skills" / skill_dir.name
        out.mkdir(parents=True)
        for name in ("SKILL.md", "skill.json"):
            shutil.copy2(skill_dir / name, out / name)
    (vendor / "tasks.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if fixtures is not None:
        fixtures.mkdir(parents=True)
        for plan in sorted((library / "plans").glob("*.skill_subgraph.json")):
            shutil.copy2(plan, fixtures / plan.name)
    (vendor / "COMMIT").write_text(commit + "\n", encoding="utf-8")
    return commit
