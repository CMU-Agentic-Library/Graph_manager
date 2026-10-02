import unittest

from graph_manager.domain.models import EntityCatalog, PlanningRequest


class EntityCatalogTest(unittest.TestCase):
    def test_catalog_parses_entity_ids_and_types(self):
        catalog = EntityCatalog.from_json(
            {"entities": [{"id": "apple", "types": ["MovableObject"]}]}
        )
        self.assertEqual(("apple",), tuple(entity.id for entity in catalog.entities))
        self.assertEqual(("MovableObject",), catalog.entities[0].types)

    def test_duplicate_entity_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate entity ID"):
            EntityCatalog.from_json(
                {
                    "entities": [
                        {"id": "apple", "types": ["MovableObject"]},
                        {"id": "apple", "types": ["ContainerObject"]},
                    ]
                }
            )

    def test_unknown_catalog_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown entity type"):
            EntityCatalog.from_json(
                {"entities": [{"id": "apple", "types": ["MovableObject", "FakeType"]}]}
            )

    def test_absent_catalog_differs_from_empty_catalog(self):
        self.assertIsNone(PlanningRequest(goal="Move the apple").entity_catalog)
        self.assertEqual((), EntityCatalog.from_json({"entities": []}).entities)


if __name__ == "__main__":
    unittest.main()
