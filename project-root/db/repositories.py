from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd
from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from db.models import (
    DailyFeature,
    DataSourceSummary,
    FeatureSnapshot,
    MLModel,
    NormalizedRecord,
    PipelineRun,
    PipelineStage,
    Prediction,
)
from db.session import persistence_enabled, session_scope

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return persistence_enabled()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Decimal):
        return float(value)
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        dt = parsed.to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
    except Exception:
        if value is None:
            return None
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _value_or_default(value: Any, default: Any) -> Any:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    return value


def _shape_value(shape: Any, idx: int) -> Optional[int]:
    if isinstance(shape, (list, tuple)) and len(shape) > idx and shape[idx] is not None:
        try:
            return int(shape[idx])
        except Exception:
            return None
    return None


def _chunked(rows: list[dict[str, Any]], size: Optional[int] = None) -> Iterable[list[dict[str, Any]]]:
    batch_size = int(size or getattr(settings, "DB_BATCH_SIZE", 1000) or 1000)
    for start in range(0, len(rows), batch_size):
        yield rows[start:start + batch_size]


def _run_pk(session, external_run_id: Optional[str]) -> Optional[uuid.UUID]:
    if not external_run_id:
        return None
    return session.scalar(select(PipelineRun.id).where(PipelineRun.run_id == external_run_id))


def create_pipeline_run(run: dict[str, Any]) -> Optional[str]:
    if not enabled():
        return None
    try:
        with session_scope() as session:
            existing = session.scalar(select(PipelineRun).where(PipelineRun.run_id == run["run_id"]))
            started_at = _dt(run.get("start_time")) or datetime.now(timezone.utc)
            if existing is None:
                existing = PipelineRun(
                    run_id=run["run_id"],
                    triggered_by=run.get("triggered_by"),
                    trigger_type=run.get("trigger_type"),
                    status=run.get("status", "Running"),
                    progress=int(run.get("overall_progress") or 0),
                    clean=bool(run.get("parameters", {}).get("clean", True)),
                    started_at=started_at,
                )
                session.add(existing)
                session.flush()
            else:
                existing.triggered_by = run.get("triggered_by", existing.triggered_by)
                existing.trigger_type = run.get("trigger_type", existing.trigger_type)
                existing.status = run.get("status", existing.status)
                existing.progress = int(run.get("overall_progress") or existing.progress or 0)
                existing.clean = bool(run.get("parameters", {}).get("clean", existing.clean))
            return str(existing.id)
    except SQLAlchemyError:
        logger.exception("Could not create pipeline run in database")
        return None


def cleanup_derived_rows_for_run(external_run_id: str) -> None:
    """Delete re-creatable derived rows for one run only.

    This preserves pipeline_runs and ml_models metadata. It is used only when
    CLEAN_DB_LATEST_ONLY=true and the caller explicitly targets a run id.
    """
    if not enabled() or not external_run_id:
        return
    try:
        with session_scope() as session:
            pk = _run_pk(session, external_run_id)
            if not pk:
                return
            for model in (
                Prediction,
                FeatureSnapshot,
                DailyFeature,
                NormalizedRecord,
                DataSourceSummary,
                PipelineStage,
            ):
                session.execute(delete(model).where(model.run_id == pk))
    except SQLAlchemyError:
        logger.exception("Could not clean derived DB rows for run %s", external_run_id)


def update_pipeline_run(run: dict[str, Any]) -> None:
    if not enabled():
        return
    try:
        with session_scope() as session:
            row = session.scalar(select(PipelineRun).where(PipelineRun.run_id == run["run_id"]))
            if row is None:
                started_at = _dt(run.get("start_time")) or datetime.now(timezone.utc)
                row = PipelineRun(
                    run_id=run["run_id"],
                    triggered_by=run.get("triggered_by"),
                    trigger_type=run.get("trigger_type"),
                    status=run.get("status", "Running"),
                    progress=int(run.get("overall_progress") or 0),
                    clean=bool(run.get("parameters", {}).get("clean", True)),
                    started_at=started_at,
                )
                session.add(row)
                session.flush()
            feature_shape = run.get("dataset_dimensions", {}).get("feature_engineered") or []
            row.status = run.get("status", row.status)
            row.triggered_by = run.get("triggered_by", row.triggered_by)
            row.trigger_type = run.get("trigger_type", row.trigger_type)
            row.progress = int(run.get("overall_progress") or 0)
            row.clean = bool(run.get("parameters", {}).get("clean", row.clean))
            row.started_at = _dt(run.get("start_time")) or row.started_at
            row.ended_at = _dt(run.get("end_time"))
            row.duration_seconds = _num(run.get("duration_seconds"))
            row.records_processed = int(run.get("metrics", {}).get("total_records_processed") or run.get("records_processed") or 0)
            row.feature_rows = int(_shape_value(feature_shape, 0) or 0)
            row.feature_columns = int(_shape_value(feature_shape, 1) or 0)
            row.ml_features_used = int(run.get("metrics", {}).get("total_features_selected_applied") or 0)
            row.predictions_count = int(run.get("metrics", {}).get("prediction_output_count") or 0)
            row.error_message = run.get("error_message")
            row.updated_at = datetime.now(timezone.utc)
    except SQLAlchemyError:
        logger.exception("Could not update pipeline run in database")


def upsert_pipeline_stage(external_run_id: str, stage: dict[str, Any], stage_order: int) -> None:
    if not enabled():
        return
    try:
        with session_scope() as session:
            pk = _run_pk(session, external_run_id)
            if not pk:
                return
            row = session.scalar(
                select(PipelineStage).where(
                    and_(PipelineStage.run_id == pk, PipelineStage.stage_name == stage.get("name"))
                )
            )
            input_shape = stage.get("input_shape")
            output_shape = stage.get("output_shape")
            error_details = stage.get("error_details") or {}
            metadata_payload = dict(stage.get("metadata") or {})
            for field in (
                "records_inserted",
                "records_rejected",
                "duplicates_removed",
                "missing_values_found",
                "missing_values_handled",
                "outliers_detected",
            ):
                if stage.get(field) is not None:
                    metadata_payload[field] = stage.get(field)
            values = {
                "stage_order": stage_order,
                "status": stage.get("status", "Pending"),
                "progress": int(stage.get("progress") or 0),
                "started_at": _dt(stage.get("start_time")),
                "ended_at": _dt(stage.get("end_time")),
                "duration_seconds": _num(stage.get("duration_seconds")),
                "records_processed": stage.get("records_processed"),
                "input_rows": _shape_value(input_shape, 0),
                "input_columns": _shape_value(input_shape, 1),
                "output_rows": _shape_value(output_shape, 0),
                "output_columns": _shape_value(output_shape, 1),
                "error_message": error_details.get("message") if isinstance(error_details, dict) else None,
                "metadata_json": _jsonable(metadata_payload),
            }
            if row is None:
                row = PipelineStage(run_id=pk, stage_name=stage.get("name"), **values)
                session.add(row)
            else:
                for key, value in values.items():
                    setattr(row, key, value)
    except SQLAlchemyError:
        logger.exception("Could not upsert pipeline stage in database")


def insert_normalized_records_batch(
    records: list[dict[str, Any]],
    external_run_id: Optional[str] = None,
    processed_file_path: Optional[str] = None,
) -> int:
    if not enabled() or not getattr(settings, "STORE_NORMALIZED_RECORDS", False) or not records:
        return 0
    inserted = 0
    try:
        with session_scope() as session:
            pk = _run_pk(session, external_run_id)
            rows = []
            for record in records:
                ts = _dt(record.get("timestamp"))
                if not ts:
                    continue
                rows.append(
                    {
                        "id": uuid.uuid4(),
                        "source": str(record.get("source") or ""),
                        "source_record_id": str(record.get("id") or record.get("source_record_id") or ""),
                        "timestamp": ts,
                        "date": ts.date(),
                        "title": record.get("title"),
                        "text": record.get("text"),
                        "tags": _jsonable(_value_or_default(record.get("tags"), [])),
                        "url": record.get("url"),
                        "techs": _jsonable(_value_or_default(record.get("techs"), [])),
                        "raw": _jsonable(_value_or_default(record.get("raw"), None)),
                        "processed_file_path": processed_file_path,
                        "run_id": pk,
                    }
                )
            for chunk in _chunked(rows):
                stmt = pg_insert(NormalizedRecord).values(chunk)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["source", "source_record_id", "timestamp", "run_id"]
                )
                result = session.execute(stmt)
                inserted += int(result.rowcount or 0)
        return inserted
    except SQLAlchemyError:
        logger.exception("Could not insert normalized records in database")
        return inserted


def upsert_data_source_summary(
    source: str,
    external_run_id: Optional[str] = None,
    file_count: Optional[int] = None,
    row_count: int = 0,
    column_count: int = 0,
    min_date: Any = None,
    max_date: Any = None,
    output_path: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    if not enabled():
        return
    try:
        with session_scope() as session:
            pk = _run_pk(session, external_run_id)
            values = {
                "id": uuid.uuid4(),
                "run_id": pk,
                "source": source,
                "file_count": file_count,
                "row_count": int(row_count or 0),
                "column_count": int(column_count or 0),
                "min_date": _date(min_date),
                "max_date": _date(max_date),
                "output_path": output_path,
                "metadata_json": _jsonable(metadata or {}),
            }
            stmt = pg_insert(DataSourceSummary).values(values)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_data_sources_summary_run_source",
                set_={
                    DataSourceSummary.run_id: values["run_id"],
                    DataSourceSummary.source: values["source"],
                    DataSourceSummary.file_count: values["file_count"],
                    DataSourceSummary.row_count: values["row_count"],
                    DataSourceSummary.column_count: values["column_count"],
                    DataSourceSummary.min_date: values["min_date"],
                    DataSourceSummary.max_date: values["max_date"],
                    DataSourceSummary.output_path: values["output_path"],
                    DataSourceSummary.metadata_json: values["metadata_json"],
                },
            )
            session.execute(stmt)
    except SQLAlchemyError:
        logger.exception("Could not upsert data source summary in database")


def insert_daily_features_batch(
    features_df: pd.DataFrame,
    external_run_id: Optional[str] = None,
) -> int:
    if not enabled() or features_df.empty:
        return 0
    inserted = 0
    try:
        with session_scope() as session:
            pk = _run_pk(session, external_run_id)
            rows: list[dict[str, Any]] = []
            for record in features_df.to_dict(orient="records"):
                feature_date = _date(record.get("date") or record.get("timestamp"))
                tech = record.get("tech") or record.get("techs")
                if not tech or not feature_date:
                    continue
                rows.append(
                    {
                        "id": uuid.uuid4(),
                        "tech": str(tech),
                        "date": feature_date,
                        "source": str(record.get("source") or "consolidated"),
                        "run_id": pk,
                        "features": _jsonable(record),
                        "technology_popularity_score": _num(record.get("technology_popularity_score")),
                        "ecosystem_momentum_score": _num(record.get("ecosystem_momentum_score")),
                    }
                )
            for chunk in _chunked(rows):
                stmt = pg_insert(DailyFeature).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_daily_features_tech_date_source_run",
                    set_={
                        "features": stmt.excluded.features,
                        "technology_popularity_score": stmt.excluded.technology_popularity_score,
                        "ecosystem_momentum_score": stmt.excluded.ecosystem_momentum_score,
                    },
                )
                result = session.execute(stmt)
                inserted += int(result.rowcount or 0)
        return inserted
    except SQLAlchemyError:
        logger.exception("Could not insert daily features in database")
        return inserted


def create_feature_snapshot(
    features_df: pd.DataFrame,
    artifact_path: str,
    feature_index_path: Optional[str] = None,
    external_run_id: Optional[str] = None,
) -> Optional[str]:
    if not enabled() or features_df.empty:
        return None
    try:
        with session_scope() as session:
            pk = _run_pk(session, external_run_id)
            existing = session.scalar(
                select(FeatureSnapshot).where(
                    and_(FeatureSnapshot.run_id == pk, FeatureSnapshot.artifact_path == artifact_path)
                )
            )
            if existing is not None:
                return str(existing.id)
            dates = pd.to_datetime(features_df["date"], errors="coerce") if "date" in features_df.columns else None
            row = FeatureSnapshot(
                run_id=pk,
                artifact_path=artifact_path,
                feature_index_path=feature_index_path,
                row_count=int(len(features_df)),
                column_count=int(features_df.shape[1]),
                technology_count=int(features_df["tech"].nunique()) if "tech" in features_df.columns else 0,
                min_date=dates.min().date() if dates is not None and dates.notna().any() else None,
                max_date=dates.max().date() if dates is not None and dates.notna().any() else None,
                feature_columns=[str(c) for c in features_df.columns],
            )
            session.add(row)
            session.flush()
            return str(row.id)
    except SQLAlchemyError:
        logger.exception("Could not create feature snapshot in database")
        return None


def _parse_training_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return _dt(value)
    return _dt(value)


def create_ml_model_record(metrics: dict[str, Any], external_run_id: Optional[str] = None) -> Optional[str]:
    if not enabled() or not metrics:
        return None
    try:
        with session_scope() as session:
            pk = _run_pk(session, external_run_id)
            model_path = str(metrics.get("model_path") or "")
            if not model_path:
                return None
            results = metrics.get("results") or {}
            accuracy = (
                results.get("random_forest_holdout", {})
                .get("report", {})
                .get("accuracy")
            )
            regression = results.get("random_forest_regressor_holdout", {})
            values = {
                "run_id": pk,
                "model_path": model_path,
                "model_name": Path(model_path).name,
                "model_type": metrics.get("model_used"),
                "training_timestamp": _parse_training_timestamp(metrics.get("training_timestamp")),
                "horizon_days": metrics.get("horizon_days"),
                "train_rows": metrics.get("training_rows"),
                "test_rows": metrics.get("testing_rows"),
                "feature_count": metrics.get("feature_count"),
                "accuracy": _num(accuracy),
                "regression_mae": _num(regression.get("mae")),
                "regression_r2": _num(regression.get("r2")),
                "holdout_confidence": _num(metrics.get("holdout_confidence")),
                "feature_columns": _jsonable(metrics.get("feature_columns") or []),
                "metrics": _jsonable(metrics),
                "feature_importance_path": metrics.get("feature_importances_path"),
                "metrics_path": metrics.get("metrics_path"),
            }
            stmt = pg_insert(MLModel).values({"id": uuid.uuid4(), **values})
            stmt = stmt.on_conflict_do_update(
                constraint="uq_ml_models_model_path",
                set_=values,
            ).returning(MLModel.id)
            model_id = session.execute(stmt).scalar_one()
            return str(model_id)
    except SQLAlchemyError:
        logger.exception("Could not create ML model record in database")
        return None


def insert_predictions_batch(
    predictions_df: pd.DataFrame,
    external_run_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> int:
    if not enabled() or predictions_df.empty:
        return 0
    inserted = 0
    try:
        with session_scope() as session:
            pk = _run_pk(session, external_run_id)
            model_pk = uuid.UUID(model_id) if model_id else None
            prediction_day = datetime.now(timezone.utc).date()
            rows = []
            for record in predictions_df.to_dict(orient="records"):
                tech = record.get("tech")
                if not tech:
                    continue
                rows.append(
                    {
                        "id": uuid.uuid4(),
                        "run_id": pk,
                        "tech": str(tech),
                        "prediction_date": prediction_day,
                        "trend_class": record.get("trend") or record.get("trend_class"),
                        "confidence": _num(record.get("confidence")),
                        "predicted_growth": _num(record.get("predicted_growth")),
                        "input_feature_date": _date(record.get("date") or record.get("input_feature_date")),
                        "model_id": model_pk,
                        "prediction_payload": _jsonable(record),
                    }
                )
            for chunk in _chunked(rows):
                stmt = pg_insert(Prediction).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_predictions_run_tech_date",
                    set_={
                        "trend_class": stmt.excluded.trend_class,
                        "confidence": stmt.excluded.confidence,
                        "predicted_growth": stmt.excluded.predicted_growth,
                        "input_feature_date": stmt.excluded.input_feature_date,
                        "model_id": stmt.excluded.model_id,
                        "prediction_payload": stmt.excluded.prediction_payload,
                    },
                )
                result = session.execute(stmt)
                inserted += int(result.rowcount or 0)
        return inserted
    except SQLAlchemyError:
        logger.exception("Could not insert predictions in database")
        return inserted


def list_pipeline_runs(limit: int = 25) -> list[dict[str, Any]]:
    if not enabled():
        return []
    try:
        with session_scope() as session:
            rows = session.scalars(
                select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)
            ).all()
            return [_pipeline_run_summary(row) for row in rows]
    except SQLAlchemyError:
        logger.exception("Could not list pipeline runs from database")
        return []


def get_latest_run_detail() -> Optional[dict[str, Any]]:
    if not enabled():
        return None
    try:
        with session_scope() as session:
            row = session.scalar(select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1))
            return _pipeline_run_detail(session, row) if row else None
    except SQLAlchemyError:
        logger.exception("Could not read latest pipeline run from database")
        return None


def get_pipeline_run_detail(external_run_id: str) -> Optional[dict[str, Any]]:
    if not enabled():
        return None
    try:
        with session_scope() as session:
            row = session.scalar(select(PipelineRun).where(PipelineRun.run_id == external_run_id))
            return _pipeline_run_detail(session, row) if row else None
    except SQLAlchemyError:
        logger.exception("Could not read pipeline run detail from database")
        return None


def get_latest_predictions() -> list[dict[str, Any]]:
    if not enabled():
        return []
    try:
        with session_scope() as session:
            latest = session.scalar(select(Prediction).order_by(Prediction.created_at.desc()).limit(1))
            if latest is None:
                return []
            criteria = [Prediction.prediction_date == latest.prediction_date]
            if latest.run_id:
                criteria.append(Prediction.run_id == latest.run_id)
            rows = session.scalars(select(Prediction).where(and_(*criteria)).order_by(Prediction.tech.asc())).all()
            return [_prediction_dict(row) for row in rows]
    except SQLAlchemyError:
        logger.exception("Could not read latest predictions from database")
        return []


def get_top_trends(limit: int = 10) -> list[dict[str, Any]]:
    if not enabled():
        return []
    try:
        with session_scope() as session:
            latest_run_id = session.scalar(select(PipelineRun.id).order_by(PipelineRun.started_at.desc()).limit(1))
            if not latest_run_id:
                return []
            max_dates = (
                select(DailyFeature.tech, func.max(DailyFeature.date).label("max_date"))
                .where(DailyFeature.run_id == latest_run_id)
                .group_by(DailyFeature.tech)
                .subquery()
            )
            rows = session.scalars(
                select(DailyFeature)
                .join(max_dates, and_(DailyFeature.tech == max_dates.c.tech, DailyFeature.date == max_dates.c.max_date))
                .where(DailyFeature.run_id == latest_run_id)
                .order_by(DailyFeature.technology_popularity_score.desc().nullslast())
                .limit(limit)
            ).all()
            return [_daily_feature_top_dict(row) for row in rows]
    except SQLAlchemyError:
        logger.exception("Could not read top trends from database")
        return []


def get_trend_history(tech: str, limit: int = 120) -> list[dict[str, Any]]:
    if not enabled():
        return []
    try:
        with session_scope() as session:
            latest_run_id = session.scalar(select(PipelineRun.id).order_by(PipelineRun.started_at.desc()).limit(1))
            criteria = [func.lower(DailyFeature.tech) == tech.casefold()]
            if latest_run_id:
                criteria.append(DailyFeature.run_id == latest_run_id)
            rows = session.scalars(
                select(DailyFeature)
                .where(and_(*criteria))
                .order_by(DailyFeature.date.desc())
                .limit(limit)
            ).all()
            return [_daily_feature_history_dict(row) for row in reversed(rows)]
    except SQLAlchemyError:
        logger.exception("Could not read trend history from database")
        return []


def get_latest_feature(tech: str) -> Optional[dict[str, Any]]:
    if not enabled():
        return None
    try:
        with session_scope() as session:
            latest_run_id = session.scalar(select(PipelineRun.id).order_by(PipelineRun.started_at.desc()).limit(1))
            criteria = [func.lower(DailyFeature.tech) == tech.casefold()]
            if latest_run_id:
                criteria.append(DailyFeature.run_id == latest_run_id)
            row = session.scalar(
                select(DailyFeature)
                .where(and_(*criteria))
                .order_by(DailyFeature.date.desc(), DailyFeature.created_at.desc())
                .limit(1)
            )
            if not row:
                return None
            features = dict(row.features or {})
            features.setdefault("tech", row.tech)
            features.setdefault("date", row.date.isoformat())
            return _jsonable(features)
    except SQLAlchemyError:
        logger.exception("Could not read latest feature from database")
        return None


def get_latest_model() -> Optional[dict[str, Any]]:
    if not enabled():
        return None
    try:
        with session_scope() as session:
            row = session.scalar(select(MLModel).order_by(MLModel.created_at.desc()).limit(1))
            return _ml_model_dict(row) if row else None
    except SQLAlchemyError:
        logger.exception("Could not read latest model metadata from database")
        return None


def get_source_summary() -> list[dict[str, Any]]:
    if not enabled():
        return []
    try:
        with session_scope() as session:
            latest_run_id = session.scalar(select(PipelineRun.id).order_by(PipelineRun.started_at.desc()).limit(1))
            if not latest_run_id:
                return []
            rows = session.scalars(
                select(DataSourceSummary)
                .where(DataSourceSummary.run_id == latest_run_id)
                .order_by(DataSourceSummary.source.asc())
            ).all()
            return [_source_summary_dict(row) for row in rows]
    except SQLAlchemyError:
        logger.exception("Could not read source summary from database")
        return []


def _pipeline_run_summary(row: PipelineRun) -> dict[str, Any]:
    return {
        "run_id": row.run_id,
        "triggered_by": row.triggered_by,
        "trigger_type": row.trigger_type,
        "status": row.status,
        "start_time": _jsonable(row.started_at),
        "end_time": _jsonable(row.ended_at),
        "duration_seconds": _jsonable(row.duration_seconds),
        "records_processed": row.records_processed,
        "features_created": row.feature_columns,
        "model_score": _latest_accuracy_for_run(row.id),
        "error_message": row.error_message,
    }


def _pipeline_run_detail(session, row: PipelineRun) -> dict[str, Any]:
    stages = session.scalars(
        select(PipelineStage)
        .where(PipelineStage.run_id == row.id)
        .order_by(PipelineStage.stage_order.asc())
    ).all()
    detail = {
        "run_id": row.run_id,
        "triggered_by": row.triggered_by,
        "trigger_type": row.trigger_type,
        "status": row.status,
        "overall_progress": row.progress,
        "current_stage": next((s.stage_name for s in stages if s.status == "Running"), None),
        "start_time": _jsonable(row.started_at),
        "end_time": _jsonable(row.ended_at),
        "duration_seconds": _jsonable(row.duration_seconds),
        "records_processed": row.records_processed,
        "features_created": row.feature_columns,
        "model_score": _latest_accuracy_for_run(row.id),
        "error_message": row.error_message,
        "parameters": {"clean": row.clean},
        "metrics": {
            "overall_pipeline_progress": row.progress,
            "current_running_stage": next((s.stage_name for s in stages if s.status == "Running"), None),
            "total_records_processed": row.records_processed,
            "total_features_created": row.feature_columns,
            "total_features_selected_applied": row.ml_features_used,
            "prediction_output_count": row.predictions_count,
            "runtime_duration_seconds": _jsonable(row.duration_seconds),
        },
        "dataset_dimensions": {
            "feature_engineered": [row.feature_rows, row.feature_columns],
            "prediction": [row.predictions_count, None],
        },
        "feature_tracking": {},
        "ml_tracking": {},
        "logs": [],
        "stages": [_stage_dict(stage) for stage in stages],
    }
    return detail


def _stage_dict(row: PipelineStage) -> dict[str, Any]:
    metadata = row.metadata_json or {}
    return {
        "id": row.stage_name.lower().replace(" ", "_").replace("/", "_"),
        "name": row.stage_name,
        "status": row.status,
        "progress": row.progress,
        "start_time": _jsonable(row.started_at),
        "end_time": _jsonable(row.ended_at),
        "duration_seconds": _jsonable(row.duration_seconds),
        "records_processed": row.records_processed,
        "records_inserted": metadata.get("records_inserted", 0),
        "records_rejected": metadata.get("records_rejected", 0),
        "duplicates_removed": metadata.get("duplicates_removed", 0),
        "missing_values_found": metadata.get("missing_values_found", 0),
        "missing_values_handled": metadata.get("missing_values_handled", 0),
        "outliers_detected": metadata.get("outliers_detected", 0),
        "input_shape": [row.input_rows, row.input_columns] if row.input_rows is not None else None,
        "output_shape": [row.output_rows, row.output_columns] if row.output_rows is not None else None,
        "error_details": {"message": row.error_message} if row.error_message else None,
        "metadata": metadata,
    }


def _prediction_dict(row: Prediction) -> dict[str, Any]:
    payload = dict(row.prediction_payload or {})
    payload.update(
        {
            "tech": row.tech,
            "date": row.input_feature_date.isoformat() if row.input_feature_date else row.prediction_date.isoformat(),
            "trend": row.trend_class,
            "confidence": _jsonable(row.confidence),
            "predicted_growth": _jsonable(row.predicted_growth),
        }
    )
    return _jsonable(payload)


def _daily_feature_top_dict(row: DailyFeature) -> dict[str, Any]:
    features = row.features or {}
    return _jsonable(
        {
            "tech": row.tech,
            "score": row.technology_popularity_score,
            "momentum": row.ecosystem_momentum_score,
            "date": row.date,
            "mentions_7d_mean": features.get("mentions_7d_mean"),
            "trend_score_avg": features.get("trend_score_avg"),
        }
    )


def _daily_feature_history_dict(row: DailyFeature) -> dict[str, Any]:
    features = row.features or {}
    keep = [
        "mentions",
        "mentions_7d_mean",
        "trend_score_avg",
        "sentiment_score_avg",
        "job_postings",
        "github_events",
        "community_engagement_sum",
        "funding_amount_musd",
    ]
    payload = {
        "date": row.date,
        "tech": row.tech,
        "technology_popularity_score": row.technology_popularity_score,
        "ecosystem_momentum_score": row.ecosystem_momentum_score,
    }
    for key in keep:
        if key in features:
            payload[key] = features[key]
    return _jsonable(payload)


def _source_summary_dict(row: DataSourceSummary) -> dict[str, Any]:
    return _jsonable(
        {
            "source": row.source,
            "file_count": row.file_count,
            "row_count": row.row_count,
            "column_count": row.column_count,
            "min_date": row.min_date,
            "max_date": row.max_date,
            "output_path": row.output_path,
            "metadata": row.metadata_json or {},
        }
    )


def _ml_model_dict(row: MLModel) -> dict[str, Any]:
    payload = {
        "id": str(row.id),
        "trained_at": row.training_timestamp,
        "horizon_days": row.horizon_days,
        "feature_columns": row.feature_columns or [],
        "artifact_path": row.model_path,
        "holdout_confidence": row.holdout_confidence,
        "feature_importances": None,
        "feature_importance_path": row.feature_importance_path,
        "metrics_path": row.metrics_path,
        "has_regression_model": row.regression_mae is not None or row.regression_r2 is not None,
        "model_type": row.model_type,
        "accuracy": row.accuracy,
        "regression_mae": row.regression_mae,
        "regression_r2": row.regression_r2,
        "metrics": row.metrics or {},
    }
    if row.feature_importance_path and Path(row.feature_importance_path).exists():
        try:
            payload["feature_importances"] = json.loads(Path(row.feature_importance_path).read_text(encoding="utf-8"))
        except Exception:
            payload["feature_importances"] = None
    return _jsonable(payload)


def _latest_accuracy_for_run(run_pk: uuid.UUID) -> Optional[float]:
    try:
        with session_scope() as session:
            row = session.scalar(
                select(MLModel)
                .where(MLModel.run_id == run_pk)
                .order_by(MLModel.created_at.desc())
                .limit(1)
            )
            return float(row.accuracy) if row and row.accuracy is not None else None
    except Exception:
        return None
