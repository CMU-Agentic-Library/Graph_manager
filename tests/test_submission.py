"""Submit tool names and argument schemas match Harness naming and the validator rules."""

import json
import unittest

from graph_manager.adapters.zenobench_library import ZenoBenchLibrary
from graph_manager.domain.subgraph import NAME
from graph_manager.domain.submission import (
    DECISION_SCHEMA,
    DECISION_TOOL_NAME,
    FROM_PATTERN,
    NAME_PATTERN,
    PLAN_TOOL_NAME,
    USE_SUBMIT_TOOLS,
    plan_schema,
)


class SubmissionSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ZenoBenchLibrary().load()
        cls.verbs = sorted(skill.verb for skill in cls.catalog.skills)

    def test_tool_names_follow_harness_mcp_naming(self):
        self.assertEqual("mcp__graph__submit_plan", PLAN_TOOL_NAME)
        self.assertEqual("mcp__graph__submit_decision", DECISION_TOOL_NAME)
        self.assertIn(PLAN_TOOL_NAME, USE_SUBMIT_TOOLS)
        self.assertIn(DECISION_TOOL_NAME, USE_SUBMIT_TOOLS)

    def test_plan_schema_fixes_fields_and_limits_skills_to_known_verbs(self):
        schema = plan_schema(self.verbs)
        subgraph = schema["properties"]["subgraphs"]["items"]
        node = subgraph["properties"]["nodes"]["items"]
        self.assertEqual(70, len(self.verbs))
        self.assertEqual(self.verbs, node["properties"]["skill"]["enum"])
        self.assertEqual(
            ["kind", "schema_version", "subgoals", "subgraphs"], sorted(schema["required"])
        )
        self.assertEqual(["args", "depends_on", "id", "skill"], sorted(node["required"]))
        for part in (schema, subgraph, node):
            self.assertFalse(part["additionalProperties"])
        json.dumps(schema)

    def test_patterns_match_the_validator_rules(self):
        self.assertEqual(NAME.pattern, NAME_PATTERN)
        self.assertRegex("n1.found_on", FROM_PATTERN)
        self.assertNotRegex("n1", FROM_PATTERN)
        self.assertNotRegex("node_1_object_tag", FROM_PATTERN)

    def test_every_output_name_fits_the_from_pattern(self):
        for skill in self.catalog.skills:
            for output in skill.outputs:
                self.assertRegex(f"n1.{output}", FROM_PATTERN)

    def test_decision_schema_allows_only_continue_and_finish(self):
        self.assertEqual(["continue", "finish"], DECISION_SCHEMA["properties"]["kind"]["enum"])
        self.assertEqual(["kind"], DECISION_SCHEMA["required"])
        self.assertFalse(DECISION_SCHEMA["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
