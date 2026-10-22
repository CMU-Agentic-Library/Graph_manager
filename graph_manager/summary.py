"""Summarize a run directory from its result.json files; runs on its own at any time.

    graph-manager-summary RUN_DIR [--by profile --by difficulty]

Planner-side numbers only: success, end reasons, replans, model turns, and calls. The
environment's own statistics (SPL, side effects) come from ZenoBench benchmark/evaluate.py.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

GROUP_KEYS = ("task_id", "profile", "variant", "difficulty", "seed", "catalog_kind")
MEANS = ("replans", "subgoal_runs", "contract_calls", "model_turns", "invalid_replies", "elapsed_s")


def load_records(run_dir: Path) -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(Path(run_dir).rglob("result.json"))
    ]


def group_value(record: dict, key: str):
    """What the service reports it ran (check_task's episode), else what was requested."""
    episode = record.get("episode") or {}
    env_episode = episode.get("env_episode") or {}
    if key in env_episode:
        return env_episode[key]
    if key == "profile" and episode.get("profile"):
        return episode["profile"]["name"]
    return record.get("request", {}).get(key)


def summarize(records: list[dict]) -> dict:
    counts = Counter(record["status"] for record in records)
    decided = counts["success"] + counts["failure"]
    episodes = [
        record["episode"]
        for record in records
        if record["status"] in ("success", "failure") and record.get("episode")
    ]
    summary = {
        "runs": len(records),
        "success": counts["success"],
        "failure": counts["failure"],
        "error": counts["error"],
        "success_rate": counts["success"] / decided if decided else None,
        "reasons": dict(Counter(episode["reason"] for episode in episodes)),
        "error_codes": dict(
            Counter(
                record["attempts"][-1]["error_code"]
                for record in records
                if record["status"] == "error" and record.get("attempts")
            )
        ),
        "restarts": sum(
            len(record.get("attempts", ())) for record in records if record["status"] != "error"
        ),
        "with_dropped": sum(1 for episode in episodes if episode.get("dropped")),
    }
    for name in MEANS:
        values = [episode[name] for episode in episodes if name in episode]
        summary[f"mean_{name}"] = sum(values) / len(values) if values else None
    return summary


def summarize_dir(run_dir: Path, by: tuple[str, ...] = ()) -> dict:
    records = load_records(run_dir)
    summary = {"overall": summarize(records), "by": {}}
    for key in by:
        groups: dict[str, list[dict]] = {}
        for record in records:
            groups.setdefault(str(group_value(record, key)), []).append(record)
        summary["by"][key] = {value: summarize(groups[value]) for value in sorted(groups)}
    return summary


def write_summary(run_dir: Path, by: tuple[str, ...] = ()) -> dict:
    summary = summarize_dir(run_dir, by)
    (Path(run_dir) / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize a graph-manager-run directory")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument(
        "--by", action="append", choices=GROUP_KEYS, default=[], help="group by; repeatable"
    )
    args = parser.parse_args(argv)
    if not args.run_dir.is_dir():
        print(f"not a directory: {args.run_dir}", file=sys.stderr)
        return 2
    print(json.dumps(write_summary(args.run_dir, tuple(args.by)), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
