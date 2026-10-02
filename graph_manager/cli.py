"""Command-line entry point for one complete-plan agent loop."""

import argparse
import json
import os
import sys
from pathlib import Path

from .adapters.openai_compatible import OpenAICompatibleModel
from .adapters.skill_library_json import JsonSkillLibraryRepository
from .application.planning_loop import PlanningFailure, PlanningLoop
from .domain.models import EntityCatalog, ObservedState, PlanningRequest

DEFAULT_LIBRARY = Path(__file__).resolve().parents[1] / "skill_library" / "skill_library.json"
IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate a task Skill plan")
    goal = parser.add_mutually_exclusive_group(required=True)
    goal.add_argument("--goal", help="task goal text")
    goal.add_argument("--goal-file", type=Path, help="UTF-8 file containing task goal text")
    parser.add_argument("--image", type=Path, help="current scene image (JPEG, PNG, WebP)")
    parser.add_argument("--observation-file", type=Path, help="optional UTF-8 observation text")
    parser.add_argument("--entity-catalog", type=Path, help="optional GT entity IDs and types JSON")
    parser.add_argument(
        "--state-file", type=Path, help="optional verified current state facts JSON"
    )
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
        goal_text = (
            args.goal if args.goal is not None else args.goal_file.read_text(encoding="utf-8")
        )
        observation = (
            args.observation_file.read_text(encoding="utf-8")
            if args.observation_file is not None
            else None
        )
        catalog = (
            EntityCatalog.from_json(json.loads(args.entity_catalog.read_text(encoding="utf-8")))
            if args.entity_catalog is not None
            else None
        )
        state = (
            ObservedState.from_json(json.loads(args.state_file.read_text(encoding="utf-8")))
            if args.state_file is not None
            else None
        )
        image = args.image.read_bytes() if args.image is not None else None
        image_mime = "image/jpeg"
        if args.image is not None:
            image_mime = IMAGE_MIME.get(args.image.suffix.lower())
            if image_mime is None:
                raise ValueError("image extension must be .jpg, .jpeg, .png, or .webp")
        request = PlanningRequest(goal_text, image, image_mime, observation, catalog, state)
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
