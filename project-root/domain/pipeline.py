from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence


PIPELINE_STAGE_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("raw_data_collection", "Raw data collection"),
    ("data_validation", "Data validation"),
    ("data_cleaning", "Data cleaning"),
    ("data_normalization_scaling", "Data normalization/scaling"),
    ("feature_engineering", "Feature engineering"),
    ("feature_selection", "Feature selection"),
    ("train_test_split", "Train/test split"),
    ("model_training", "Model training"),
    ("model_evaluation", "Model evaluation"),
    ("prediction_generation", "Prediction/forecast generation"),
    ("final_output_creation", "Final output creation"),
    ("dashboard_refresh", "Dashboard refresh"),
)

TERMINAL_PIPELINE_STATUSES = frozenset({"Completed", "Failed", "Cancelled"})


@dataclass(frozen=True)
class DatasetShape:
    rows: int = 0
    columns: int = 0

    @classmethod
    def from_sequence(cls, value: Sequence[Any] | None) -> "DatasetShape":
        if not value or len(value) < 2:
            return cls()
        return cls(rows=int(value[0] or 0), columns=int(value[1] or 0))

    def as_list(self) -> list[int]:
        return [self.rows, self.columns]


@dataclass
class PipelineStageContract:
    id: str
    name: str
    status: str = "Pending"
    progress: int = 0
    start_time: datetime | str | None = None
    end_time: datetime | str | None = None
    duration_seconds: float | None = None
    records_processed: int = 0
    input_shape: DatasetShape | None = None
    output_shape: DatasetShape | None = None
    error_details: Mapping[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineRunContract:
    run_id: str
    triggered_by: str
    trigger_type: str = "Full"
    status: str = "Running"
    overall_progress: int = 0
    current_stage: str | None = None
    start_time: datetime | str | None = None
    end_time: datetime | str | None = None
    duration_seconds: float | None = None
    records_processed: int = 0
    features_created: int = 0
    model_score: float | None = None
    error_message: str | None = None
