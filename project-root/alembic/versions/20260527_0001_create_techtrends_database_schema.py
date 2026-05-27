"""create techtrends database schema

Revision ID: 20260527_0001
Revises:
Create Date: 2026-05-27 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260527_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("triggered_by", sa.String(length=100), nullable=True),
        sa.Column("trigger_type", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("clean", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(14, 3), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("feature_rows", sa.Integer(), nullable=False),
        sa.Column("feature_columns", sa.Integer(), nullable=False),
        sa.Column("ml_features_used", sa.Integer(), nullable=False),
        sa.Column("predictions_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_pipeline_runs_run_id", "pipeline_runs", ["run_id"])
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])

    op.create_table(
        "pipeline_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_name", sa.String(length=128), nullable=False),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(14, 3), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=True),
        sa.Column("input_rows", sa.Integer(), nullable=True),
        sa.Column("input_columns", sa.Integer(), nullable=True),
        sa.Column("output_rows", sa.Integer(), nullable=True),
        sa.Column("output_columns", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "stage_name", name="uq_pipeline_stage_run_stage"),
    )
    op.create_index("ix_pipeline_stages_run_order", "pipeline_stages", ["run_id", "stage_order"])
    op.create_index("ix_pipeline_stages_status", "pipeline_stages", ["status"])

    op.create_table(
        "normalized_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("techs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("processed_file_path", sa.Text(), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_record_id", "timestamp", "run_id", name="uq_normalized_record_per_run"),
    )
    op.create_index("ix_normalized_records_source", "normalized_records", ["source"])
    op.create_index("ix_normalized_records_source_date", "normalized_records", ["source", "date"])
    op.create_index("ix_normalized_records_timestamp", "normalized_records", ["timestamp"])
    op.create_index("ix_normalized_records_date", "normalized_records", ["date"])
    op.create_index("ix_normalized_records_techs_gin", "normalized_records", ["techs"], postgresql_using="gin")
    op.create_index("ix_normalized_records_tags_gin", "normalized_records", ["tags"], postgresql_using="gin")

    op.create_table(
        "daily_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tech", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("technology_popularity_score", sa.Numeric(18, 6), nullable=True),
        sa.Column("ecosystem_momentum_score", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tech", "date", "source", "run_id", name="uq_daily_features_tech_date_source_run"),
    )
    op.create_index("ix_daily_features_tech", "daily_features", ["tech"])
    op.create_index("ix_daily_features_date", "daily_features", ["date"])
    op.create_index("ix_daily_features_tech_date", "daily_features", ["tech", "date"])
    op.create_index("ix_daily_features_run_id", "daily_features", ["run_id"])
    op.create_index("ix_daily_features_features_gin", "daily_features", ["features"], postgresql_using="gin")

    op.create_table(
        "feature_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("feature_index_path", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("column_count", sa.Integer(), nullable=False),
        sa.Column("technology_count", sa.Integer(), nullable=False),
        sa.Column("min_date", sa.Date(), nullable=True),
        sa.Column("max_date", sa.Date(), nullable=True),
        sa.Column("feature_columns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feature_snapshots_run_id", "feature_snapshots", ["run_id"])

    op.create_table(
        "ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_path", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("model_type", sa.String(length=100), nullable=True),
        sa.Column("training_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=True),
        sa.Column("train_rows", sa.Integer(), nullable=True),
        sa.Column("test_rows", sa.Integer(), nullable=True),
        sa.Column("feature_count", sa.Integer(), nullable=True),
        sa.Column("accuracy", sa.Numeric(18, 8), nullable=True),
        sa.Column("regression_mae", sa.Numeric(18, 8), nullable=True),
        sa.Column("regression_r2", sa.Numeric(18, 8), nullable=True),
        sa.Column("holdout_confidence", sa.Numeric(18, 8), nullable=True),
        sa.Column("feature_columns", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("feature_importance_path", sa.Text(), nullable=True),
        sa.Column("metrics_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_path", name="uq_ml_models_model_path"),
    )
    op.create_index("ix_ml_models_run_id", "ml_models", ["run_id"])

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tech", sa.String(length=255), nullable=False),
        sa.Column("prediction_date", sa.Date(), nullable=False),
        sa.Column("trend_class", sa.String(length=50), nullable=True),
        sa.Column("confidence", sa.Numeric(18, 8), nullable=True),
        sa.Column("predicted_growth", sa.Numeric(18, 8), nullable=True),
        sa.Column("input_feature_date", sa.Date(), nullable=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prediction_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["ml_models.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "tech", "prediction_date", name="uq_predictions_run_tech_date"),
    )
    op.create_index("ix_predictions_tech", "predictions", ["tech"])
    op.create_index("ix_predictions_prediction_date", "predictions", ["prediction_date"])
    op.create_index("ix_predictions_tech_prediction_date", "predictions", ["tech", "prediction_date"])
    op.create_index("ix_predictions_run_id", "predictions", ["run_id"])
    op.create_index("ix_predictions_trend_class", "predictions", ["trend_class"])

    op.create_table(
        "data_sources_summary",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("column_count", sa.Integer(), nullable=False),
        sa.Column("min_date", sa.Date(), nullable=True),
        sa.Column("max_date", sa.Date(), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "source", name="uq_data_sources_summary_run_source"),
    )
    op.create_index("ix_data_sources_summary_source", "data_sources_summary", ["source"])
    op.create_index("ix_data_sources_summary_run_id", "data_sources_summary", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_data_sources_summary_run_id", table_name="data_sources_summary")
    op.drop_index("ix_data_sources_summary_source", table_name="data_sources_summary")
    op.drop_table("data_sources_summary")

    op.drop_index("ix_predictions_trend_class", table_name="predictions")
    op.drop_index("ix_predictions_run_id", table_name="predictions")
    op.drop_index("ix_predictions_tech_prediction_date", table_name="predictions")
    op.drop_index("ix_predictions_prediction_date", table_name="predictions")
    op.drop_index("ix_predictions_tech", table_name="predictions")
    op.drop_table("predictions")

    op.drop_index("ix_ml_models_run_id", table_name="ml_models")
    op.drop_table("ml_models")

    op.drop_index("ix_feature_snapshots_run_id", table_name="feature_snapshots")
    op.drop_table("feature_snapshots")

    op.drop_index("ix_daily_features_features_gin", table_name="daily_features")
    op.drop_index("ix_daily_features_run_id", table_name="daily_features")
    op.drop_index("ix_daily_features_tech_date", table_name="daily_features")
    op.drop_index("ix_daily_features_date", table_name="daily_features")
    op.drop_index("ix_daily_features_tech", table_name="daily_features")
    op.drop_table("daily_features")

    op.drop_index("ix_normalized_records_tags_gin", table_name="normalized_records")
    op.drop_index("ix_normalized_records_techs_gin", table_name="normalized_records")
    op.drop_index("ix_normalized_records_date", table_name="normalized_records")
    op.drop_index("ix_normalized_records_timestamp", table_name="normalized_records")
    op.drop_index("ix_normalized_records_source_date", table_name="normalized_records")
    op.drop_index("ix_normalized_records_source", table_name="normalized_records")
    op.drop_table("normalized_records")

    op.drop_index("ix_pipeline_stages_status", table_name="pipeline_stages")
    op.drop_index("ix_pipeline_stages_run_order", table_name="pipeline_stages")
    op.drop_table("pipeline_stages")

    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_run_id", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
