"""Read planning inputs for the public planning command."""

import argparse
from pathlib import Path

from .domain.models import PlanningRequest

IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def add_request_arguments(parser: argparse.ArgumentParser) -> None:
    goal = parser.add_mutually_exclusive_group(required=True)
    goal.add_argument("--goal", help="task goal text")
    goal.add_argument("--goal-file", type=Path, help="UTF-8 file containing task goal text")
    parser.add_argument("--image", type=Path, help="current scene image (JPEG, PNG, WebP)")
    parser.add_argument("--observation-file", type=Path, help="optional UTF-8 observation text")


def read_request(args: argparse.Namespace) -> PlanningRequest:
    goal_text = args.goal if args.goal is not None else args.goal_file.read_text(encoding="utf-8")
    observation = (
        args.observation_file.read_text(encoding="utf-8")
        if args.observation_file is not None
        else None
    )
    image = args.image.read_bytes() if args.image is not None else None
    image_mime = "image/jpeg"
    if args.image is not None:
        image_mime = IMAGE_MIME.get(args.image.suffix.lower())
        if image_mime is None:
            raise ValueError("image extension must be .jpg, .jpeg, .png, or .webp")
    return PlanningRequest(goal_text, image, image_mime, observation)
