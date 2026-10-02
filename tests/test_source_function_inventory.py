"""The full source inventory is documentation; only nine functions are Skills."""

import ast
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "ZenoBench" / "zeno_skills" / "skills.py"
SKILLS = ROOT / "skill_library" / "skills"
INVENTORY = ROOT / "docs" / "zenobench-skills-function-inventory.md"
EXPOSED = {
    "navigate",
    "open_articulated",
    "close_articulated",
    "pick",
    "push",
    "place",
    "place_on",
    "press_microwave_start",
    "cycle_microwave_door",
}


def documented_callables():
    found = []
    anonymous_section = False
    for line in INVENTORY.read_text().splitlines():
        if line.startswith("## "):
            anonymous_section = line == "## Anonymous sort-key functions"
        match = re.match(r"^\|\s*`([^`]+)`[^|]*\|\s*(\d+)\s*\|", line)
        if match:
            name, line_number = match.groups()
            found.append((f"{name}.<lambda>" if anonymous_section else name, int(line_number)))
    return found


def source_callables():
    found = []

    def visit(node, scope=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = f"{scope}.{child.name}" if scope else child.name
                found.append((qualname, child.lineno))
                visit(child, qualname)
            elif isinstance(child, ast.Lambda):
                found.append((f"{scope}.<lambda>", child.lineno))
                visit(child, scope)
            else:
                visit(child, scope)

    visit(ast.parse(SOURCE.read_text()))
    return found


class SourceFunctionInventoryTest(unittest.TestCase):
    def test_inventory_documents_all_functions_but_only_nine_are_skills(self):
        documented = documented_callables()
        self.assertEqual(44, len(documented))
        contracts = [json.loads(path.read_text()) for path in sorted(SKILLS.glob("skill_*.json"))]
        self.assertEqual(9, len(contracts))
        actual = {
            (c["source_function"]["qualname"], c["source_function"]["line"]) for c in contracts
        }
        self.assertEqual(EXPOSED, {name for name, _ in actual})
        self.assertTrue(actual <= set(documented))
        self.assertEqual(35, len(set(documented) - actual))

        for link in re.findall(
            r"\]\((\.\./skill_library/skills/[^)]+\.json)\)", INVENTORY.read_text()
        ):
            self.assertTrue((INVENTORY.parent / link).exists(), link)

    @unittest.skipUnless(SOURCE.exists(), "Sibling ZenoBench checkout is needed for AST comparison")
    def test_saved_inventory_matches_source_ast(self):
        self.assertEqual(set(documented_callables()), set(source_callables()))


if __name__ == "__main__":
    unittest.main()
