import tempfile
import unittest
from pathlib import Path

from infrastructure.storage.pipeline_state import PipelineStateFileRepository


class PipelineStateFileRepositoryTests(unittest.TestCase):
    def test_state_repository_preserves_current_and_history_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = PipelineStateFileRepository(Path(temp_dir))
            run = {"run_id": "run-test", "status": "Running", "overall_progress": 50}

            repo.write_current(run)
            repo.write_runs([run])

            self.assertEqual(run, repo.read_current())
            self.assertEqual([run], repo.read_runs())
            self.assertTrue((Path(temp_dir) / "pipeline_current.json").exists())
            self.assertTrue((Path(temp_dir) / "pipeline_runs.json").exists())

    def test_corrupt_or_missing_files_fall_back_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir)
            (state_dir / "pipeline_runs.json").write_text("{not-json", encoding="utf-8")
            (state_dir / "pipeline_current.json").write_text("[unexpected]", encoding="utf-8")

            repo = PipelineStateFileRepository(state_dir)

            self.assertEqual([], repo.read_runs())
            self.assertIsNone(repo.read_current())


if __name__ == "__main__":
    unittest.main()
