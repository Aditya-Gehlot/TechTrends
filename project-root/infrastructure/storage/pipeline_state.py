from __future__ import annotations

from pathlib import Path
from typing import Any

from infrastructure.storage.json_store import JsonFileStore


class PipelineStateFileRepository:
    """File-backed state repository for pipeline runs.

    This preserves the existing `.state/pipeline_current.json` and
    `.state/pipeline_runs.json` files while hiding their storage mechanics from
    the runner.
    """

    def __init__(self, state_dir: Path | str) -> None:
        self.state_dir = Path(state_dir)
        self.runs_store: JsonFileStore[list[dict[str, Any]]] = JsonFileStore(
            self.state_dir / "pipeline_runs.json",
            list,
        )
        self.current_store: JsonFileStore[dict[str, Any] | None] = JsonFileStore(
            self.state_dir / "pipeline_current.json",
            lambda: None,
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.runs_store.path.exists():
            self.write_runs([])

    def read_runs(self) -> list[dict[str, Any]]:
        runs = self.runs_store.read()
        return runs if isinstance(runs, list) else []

    def write_runs(self, runs: list[dict[str, Any]]) -> None:
        self.runs_store.write(runs)

    def read_current(self) -> dict[str, Any] | None:
        current = self.current_store.read()
        return current if isinstance(current, dict) else None

    def write_current(self, run: dict[str, Any]) -> None:
        self.current_store.write(run)
