"""Read the ZenoBench Skill Library files synced into this package."""

import json
from dataclasses import dataclass
from pathlib import Path

from ..domain.skills import SkillCatalog, SkillSpec

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "zenobench"


@dataclass(frozen=True)
class TaskEntry:
    """One task of the synced index: never its goal, routes, or variant descriptions."""

    task_id: str
    catalog: str  # the ZenoBench catalog file, such as benchmark/v3/tasks.json
    default_profile: str
    variants: dict[str, str]  # variant name -> difficulty (easy, medium, hard, diagnostic)


class ZenoBenchLibrary:
    def __init__(self, root: Path = DEFAULT_ROOT):
        self.root = Path(root).resolve()

    @property
    def skills_dir(self) -> Path:
        return self.root / "skills"

    @property
    def commit(self) -> str:
        return (self.root / "COMMIT").read_text(encoding="utf-8").strip()

    def load(self) -> SkillCatalog:
        paths = sorted(self.skills_dir.glob("*/skill.json"))
        if not paths:
            raise ValueError(f"no skill.json under {self.skills_dir}")
        return SkillCatalog(
            tuple(SkillSpec.from_json(json.loads(p.read_text(encoding="utf-8"))) for p in paths)
        )

    def tasks(self) -> dict[str, TaskEntry]:
        data = json.loads((self.root / "tasks.json").read_text(encoding="utf-8"))
        return {task["task_id"]: TaskEntry(**task) for task in data["tasks"]}

    def task_ids(self) -> tuple[str, ...]:
        return tuple(self.tasks())

    def predicate_meanings(self) -> dict[str, str]:
        """Predicate name -> plain-language meaning, from every skill's conditions."""
        meanings: dict[str, str] = {}
        for path in sorted(self.skills_dir.glob("*/skill.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            for condition in (*data.get("preconditions", ()), *data.get("postconditions", ())):
                name, meaning = condition.get("name"), condition.get("meaning")
                if isinstance(name, str) and isinstance(meaning, str) and meaning:
                    meanings.setdefault(name, meaning)
        return meanings
