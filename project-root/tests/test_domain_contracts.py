import unittest

from domain.pipeline import (
    PIPELINE_STAGE_DEFINITIONS,
    TERMINAL_PIPELINE_STATUSES,
    DatasetShape,
    PipelineRunContract,
)


class DomainContractTests(unittest.TestCase):
    def test_pipeline_stage_definitions_are_stable_and_unique(self) -> None:
        stage_ids = [stage_id for stage_id, _ in PIPELINE_STAGE_DEFINITIONS]

        self.assertEqual(12, len(PIPELINE_STAGE_DEFINITIONS))
        self.assertEqual(len(stage_ids), len(set(stage_ids)))
        self.assertEqual("raw_data_collection", stage_ids[0])
        self.assertEqual("dashboard_refresh", stage_ids[-1])

    def test_dataset_shape_keeps_existing_list_shape_contract(self) -> None:
        self.assertEqual([100, 25], DatasetShape.from_sequence([100, 25]).as_list())
        self.assertEqual([0, 0], DatasetShape.from_sequence(None).as_list())

    def test_pipeline_run_contract_defaults_match_runtime_statuses(self) -> None:
        run = PipelineRunContract(run_id="run-test", triggered_by="unit-test")

        self.assertEqual("Running", run.status)
        self.assertIn("Completed", TERMINAL_PIPELINE_STATUSES)
        self.assertEqual(0, run.overall_progress)


if __name__ == "__main__":
    unittest.main()
