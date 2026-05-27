from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class NormalizedRecordContract:
    source: str
    source_record_id: str
    timestamp: datetime | str
    title: str | None = None
    text: str | None = None
    tags: list[str] = field(default_factory=list)
    url: str | None = None
    techs: list[str] = field(default_factory=list)
    raw: dict[str, Any] | None = None
    processed_file_path: str | None = None
    run_id: str | None = None


@dataclass
class FeatureSnapshotContract:
    artifact_path: str
    row_count: int
    column_count: int
    technology_count: int
    min_date: date | str | None = None
    max_date: date | str | None = None
    feature_index_path: str | None = None
    feature_columns: list[str] = field(default_factory=list)
    run_id: str | None = None


@dataclass
class ModelMetadataContract:
    model_path: str
    model_name: str
    model_type: str
    training_timestamp: datetime | str | None = None
    horizon_days: int | None = None
    train_rows: int = 0
    test_rows: int = 0
    feature_count: int = 0
    accuracy: float | None = None
    regression_mae: float | None = None
    regression_r2: float | None = None
    holdout_confidence: float | None = None
    feature_columns: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    feature_importance_path: str | None = None
    metrics_path: str | None = None
    run_id: str | None = None


@dataclass
class PredictionContract:
    tech: str
    prediction_date: date | str
    trend_class: str | None = None
    confidence: float | None = None
    predicted_growth: float | None = None
    input_feature_date: date | str | None = None
    prediction_payload: dict[str, Any] | None = None
    run_id: str | None = None
    model_id: str | None = None


@dataclass
class SourceSummaryContract:
    source: str
    row_count: int
    column_count: int = 0
    file_count: int | None = None
    min_date: date | str | None = None
    max_date: date | str | None = None
    output_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None
