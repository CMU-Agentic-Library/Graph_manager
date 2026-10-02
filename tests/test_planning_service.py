import json
import unittest
from pathlib import Path

from graph_manager.domain import EntityCatalog, PlanningRequest
from graph_manager.openai_compatible import ModelAdapterError
from graph_manager.planning import PlanningFailure, PlanningService
from graph_manager.repository import JsonSkillLibraryRepository


ROOT = Path(__file__).resolve().parents[1]
PLAN = {"schema_version": 1, "kind": "subgoal_plan", "subgoals": [
    {"id": "sg_1", "goal": "Hold the apple"},
    {"id": "sg_2", "goal": "Put the apple in the basket"},
]}


def graph(subgoal_id, skill_id, args):
    return {"schema_version": 1, "kind": "skill_subgraph", "subgoal_id": subgoal_id,
            "nodes": [{"id": "n1", "skill_id": skill_id, "args": args, "depends_on": []}]}


class SequenceModel:
    def __init__(self, outputs):
        self.outputs = iter(json.dumps(output) if isinstance(output, dict) else output for output in outputs)
        self.calls = []

    def generate(self, prompt, image=None, image_mime="image/jpeg"):
        self.calls.append((prompt, image, image_mime))
        return next(self.outputs)


class PlanningServiceTest(unittest.TestCase):
    def service(self, model):
        return PlanningService(JsonSkillLibraryRepository(ROOT / "skill_library" / "skill_library.json"), model)

    def outputs(self):
        return [PLAN, graph("sg_1", "skill_004", {"object": {"ref": "apple"}}),
                graph("sg_2", "skill_006", {"object": {"ref": "apple"},
                                                "container": {"ref": "basket"}})]

    def test_two_stage_flow_uses_all_skills_and_one_graph_per_subgoal(self):
        model = SequenceModel(self.outputs())
        catalog = EntityCatalog.from_json({"entities": [
            {"id": "apple", "types": ["MovableObject"]},
            {"id": "basket", "types": ["ContainerObject"]},
        ]})
        result = self.service(model).plan(PlanningRequest(
            goal="Put the apple in the basket", image=b"fake-jpeg", entity_catalog=catalog))
        self.assertEqual(3, len(model.calls))
        self.assertEqual(["sg_1", "sg_2"], [g["subgoal_id"] for g in result.subgraphs])
        self.assertTrue(result.grounded)
        for prompt, image, mime in model.calls:
            self.assertIn('"skill_009"', prompt)
            self.assertIn('"id": "apple"', prompt)
            self.assertEqual(b"fake-jpeg", image)
            self.assertEqual("image/jpeg", mime)
        self.assertIn('"id": "sg_1"', model.calls[1][0])
        self.assertIn('"id": "sg_2"', model.calls[2][0])

    def test_catalog_is_truly_optional_and_refs_remain_unresolved(self):
        model = SequenceModel(self.outputs())
        result = self.service(model).plan(PlanningRequest(goal="Put apple away", observation="Table visible"))
        self.assertFalse(result.grounded)
        self.assertEqual(3, len(model.calls))
        self.assertTrue(all("GT entity catalog" not in prompt for prompt, _, _ in model.calls))
        self.assertIn("Table visible", model.calls[0][0])

    def test_wrong_subgoal_graph_stops_and_retains_raw_output(self):
        model = SequenceModel([PLAN, graph("sg_2", "skill_004", {"object": {"ref": "apple"}})])
        with self.assertRaises(PlanningFailure) as caught:
            self.service(model).plan(PlanningRequest(goal="Put apple away"))
        self.assertEqual("sg_1", caught.exception.stage)
        self.assertEqual("wrong_target_subgoal", caught.exception.issues[0].code)
        self.assertEqual(2, len(caught.exception.raw_outputs))

    def test_invalid_first_json_stops_before_graph_requests(self):
        model = SequenceModel(["{not json"])
        with self.assertRaises(PlanningFailure) as caught:
            self.service(model).plan(PlanningRequest(goal="Put apple away"))
        self.assertEqual("subgoals", caught.exception.stage)
        self.assertEqual(1, len(model.calls))
        self.assertEqual("json_syntax", caught.exception.issues[0].code)

    def test_truncated_model_response_is_saved_in_failure(self):
        class TruncatedModel:
            def generate(self, _prompt, _image=None, _image_mime="image/jpeg"):
                raise ModelAdapterError("finish_reason=length", raw_content='{"partial":true}')

        with self.assertRaises(PlanningFailure) as caught:
            self.service(TruncatedModel()).plan(PlanningRequest(goal="Hold apple"))
        self.assertEqual("subgoals", caught.exception.raw_outputs[0]["stage"])
        self.assertEqual('{"partial":true}', caught.exception.raw_outputs[0]["text"])


if __name__ == "__main__":
    unittest.main()
