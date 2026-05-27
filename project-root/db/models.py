from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


JSONBType = JSONB
UUIDType = UUID(as_uuid=True)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PipelineRun(Base, CreatedAtMixin):
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trigger_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clean: Mapped[bool] = mapped_column(default=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 3), nullable=True)
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_columns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ml_features_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    predictions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    stages: Mapped[list["PipelineStage"]] = relationship(back_populates="run")


class PipelineStage(Base, CreatedAtMixin):
    __tablename__ = "pipeline_stages"
    __table_args__ = (
        UniqueConstraint("run_id", "stage_name", name="uq_pipeline_stage_run_stage"),
        Index("ix_pipeline_stages_run_order", "run_id", "stage_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(128), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 3), nullable=True)
    records_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    input_rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    input_columns: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_columns: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONBType, nullable=True)

    run: Mapped[PipelineRun] = relationship(back_populates="stages")


class NormalizedRecord(Base, CreatedAtMixin):
    __tablename__ = "normalized_records"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_record_id",
            "timestamp",
            "run_id",
            name="uq_normalized_record_per_run",
        ),
        Index("ix_normalized_records_source_date", "source", "date"),
        Index("ix_normalized_records_timestamp", "timestamp"),
        Index("ix_normalized_records_techs_gin", "techs", postgresql_using="gin"),
        Index("ix_normalized_records_tags_gin", "tags", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[list[Any]] = mapped_column(JSONBType, nullable=False, default=list)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    techs: Mapped[list[Any]] = mapped_column(JSONBType, nullable=False, default=list)
    raw: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONBType, nullable=True)
    processed_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True)


class DailyFeature(Base, CreatedAtMixin):
    __tablename__ = "daily_features"
    __table_args__ = (
        UniqueConstraint("tech", "date", "source", "run_id", name="uq_daily_features_tech_date_source_run"),
        Index("ix_daily_features_tech_date", "tech", "date"),
        Index("ix_daily_features_run_id", "run_id"),
        Index("ix_daily_features_features_gin", "features", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    tech: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True)
    features: Mapped[dict[str, Any]] = mapped_column(JSONBType, nullable=False)
    technology_popularity_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    ecosystem_momentum_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)


class FeatureSnapshot(Base, CreatedAtMixin):
    __tablename__ = "feature_snapshots"
    __table_args__ = (Index("ix_feature_snapshots_run_id", "run_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    feature_index_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False)
    technology_count: Mapped[int] = mapped_column(Integer, nullable=False)
    min_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    max_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    feature_columns: Mapped[list[Any]] = mapped_column(JSONBType, nullable=False, default=list)


class MLModel(Base, CreatedAtMixin):
    __tablename__ = "ml_models"
    __table_args__ = (
        UniqueConstraint("model_path", name="uq_ml_models_model_path"),
        Index("ix_ml_models_run_id", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True)
    model_path: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    training_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    horizon_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    train_rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    test_rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feature_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    regression_mae: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    regression_r2: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    holdout_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    feature_columns: Mapped[Optional[list[Any]]] = mapped_column(JSONBType, nullable=True)
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONBType, nullable=True)
    feature_importance_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Prediction(Base, CreatedAtMixin):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("run_id", "tech", "prediction_date", name="uq_predictions_run_tech_date"),
        Index("ix_predictions_tech_prediction_date", "tech", "prediction_date"),
        Index("ix_predictions_run_id", "run_id"),
        Index("ix_predictions_trend_class", "trend_class"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True)
    tech: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    prediction_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    trend_class: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    predicted_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    input_feature_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType, ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True)
    prediction_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONBType, nullable=True)


class DataSourceSummary(Base, CreatedAtMixin):
    __tablename__ = "data_sources_summary"
    __table_args__ = (
        UniqueConstraint("run_id", "source", name="uq_data_sources_summary_run_source"),
        Index("ix_data_sources_summary_source", "source"),
        Index("ix_data_sources_summary_run_id", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    file_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    max_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONBType, nullable=True)
