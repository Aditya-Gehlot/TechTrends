"""Backfill PostgreSQL from existing derived TechTrends artifacts.

This intentionally does not import raw generated Data/*.csv files. It starts at
processed normalized parquet and derived pipeline artifacts.

Usage:
    ENABLE_DB_PERSISTENCE=true python -m scripts.backfill_db_from_existing_artifacts
    ENABLE_DB_PERSISTENCE=true python -m scripts.backfill_db_from_existing_artifacts --store-normalized-records
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from config import settings
from db import repositories as db_repo

logger = logging.getLogger(__name__)


def _read_json(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Could not read %s", path)
        return default


def _dedupe_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for run in runs:
        run_id = run.get("run_id")
        if not run_id or run_id in seen:
            continue
        seen.add(run_id)
        result.append(run)
    return result


def _load_state_runs() -> list[dict[str, Any]]:
    runs_path = Path(settings.STATE_DIR) / "pipeline_runs.json"
    current_path = Path(settings.STATE_DIR) / "pipeline_current.json"
    runs = _read_json(runs_path, [])
    current = _read_json(current_path, None)
    if isinstance(current, dict):
        runs.insert(0, current)
    return _dedupe_runs([run for run in runs if isinstance(run, dict)])


def backfill_runs(runs: list[dict[str, Any]]) -> dict[str, str]:
    run_map: dict[str, str] = {}
    for run in runs:
        db_id = db_repo.create_pipeline_run(run)
        db_repo.update_pipeline_run(run)
        if db_id:
            run_map[run["run_id"]] = db_id
        for order, stage in enumerate(run.get("stages", []), start=1):
            db_repo.upsert_pipeline_stage(run["run_id"], stage, order)
    return run_map


def latest_run_id(runs: list[dict[str, Any]]) -> str | None:
    return runs[0].get("run_id") if runs else None


def model_path_to_run_id(runs: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for run in runs:
        run_id = run.get("run_id")
        model_path = (run.get("ml_tracking") or {}).get("model_file_path")
        if run_id and model_path:
            mapping[str(model_path)] = run_id
    return mapping


def backfill_processed(run_id: str | None, store_normalized_records: bool) -> None:
    processed_dir = Path(settings.PROCESSED_DIR)
    if not processed_dir.exists():
        return

    original_store_setting = settings.STORE_NORMALIZED_RECORDS
    settings.STORE_NORMALIZED_RECORDS = bool(store_normalized_records)
    try:
        for source_dir in sorted(p for p in processed_dir.iterdir() if p.is_dir()):
            files = sorted(source_dir.rglob("*.parquet"))
            if not files:
                continue
            total_rows = 0
            columns = set()
            min_date = None
            max_date = None
            for file_path in files:
                try:
                    df = pd.read_parquet(file_path)
                except Exception:
                    logger.exception("Could not read processed parquet %s", file_path)
                    continue
                total_rows += len(df)
                columns.update(str(c) for c in df.columns)
                if "timestamp" in df.columns:
                    dates = pd.to_datetime(df["timestamp"], errors="coerce").dropna()
                    if not dates.empty:
                        local_min = dates.min().date()
                        local_max = dates.max().date()
                        min_date = local_min if min_date is None or local_min < min_date else min_date
                        max_date = local_max if max_date is None or local_max > max_date else max_date
                if store_normalized_records and source_dir.name != "_dimensions":
                    db_repo.insert_normalized_records_batch(
                        df.to_dict(orient="records"),
                        external_run_id=run_id,
                        processed_file_path=str(file_path),
                    )
            db_repo.upsert_data_source_summary(
                source=source_dir.name,
                external_run_id=run_id,
                file_count=len(files),
                row_count=total_rows,
                column_count=len(columns),
                min_date=min_date,
                max_date=max_date,
                output_path=str(source_dir),
                metadata={"format": "parquet", "backfilled": True},
            )
    finally:
        settings.STORE_NORMALIZED_RECORDS = original_store_setting


def backfill_features(run_id: str | None) -> None:
    feature_path = Path(settings.FEATURE_STORE_DIR) / "features_all.parquet"
    if not feature_path.exists():
        return
    df = pd.read_parquet(feature_path)
    db_repo.insert_daily_features_batch(df, external_run_id=run_id)
    db_repo.create_feature_snapshot(
        df,
        artifact_path=str(feature_path),
        feature_index_path=str(Path(settings.FEATURE_STORE_DIR) / "feature_index.json"),
        external_run_id=run_id,
    )


def backfill_predictions(run_id: str | None) -> None:
    path = Path(settings.FEATURE_STORE_DIR) / "predictions_latest.json"
    if not path.exists():
        return
    records = _read_json(path, [])
    if records:
        db_repo.insert_predictions_batch(pd.DataFrame(records), external_run_id=run_id)


def backfill_models(path_run_map: dict[str, str]) -> None:
    artifacts_dir = Path(settings.ML_MODELS_DIR).parents[0] / "artifacts"
    for metrics_path in sorted(artifacts_dir.glob("metrics_*.json")):
        metrics = _read_json(metrics_path, {})
        if not metrics:
            continue
        metrics["metrics_path"] = str(metrics_path)
        timestamp = metrics.get("training_timestamp")
        fi_path = artifacts_dir / f"feature_importances_{timestamp}.json"
        if fi_path.exists():
            metrics["feature_importances_path"] = str(fi_path)
        run_id = path_run_map.get(str(metrics.get("model_path")))
        db_repo.create_ml_model_record(metrics, external_run_id=run_id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--store-normalized-records",
        action="store_true",
        help="Also backfill processed normalized records. This can insert hundreds of thousands of rows.",
    )
    args = parser.parse_args()

    if not db_repo.enabled():
        raise SystemExit("Database persistence is disabled. Set ENABLE_DB_PERSISTENCE=true and DATABASE_URL first.")

    runs = _load_state_runs()
    backfill_runs(runs)
    run_id = latest_run_id(runs)
    backfill_processed(run_id, store_normalized_records=args.store_normalized_records)
    backfill_features(run_id)
    backfill_models(model_path_to_run_id(runs))
    backfill_predictions(run_id)
    logger.info("Database backfill complete")


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(levelname)s:%(name)s:%(message)s")
    main()

