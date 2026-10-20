"""Read the ZenoBench Skill Library files synced into this package."""

import json
from pathlib import Path

from ..domain.skills import SkillCatalog, SkillSpec

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "zenobench"


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

    def task_ids(self) -> tuple[str, ...]:
        data = json.loads((self.root / "tasks.json").read_text(encoding="utf-8"))
        return tuple(task["id"] for task in data["tasks"])

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
