"""UI/API pipeline runner with durable run history.

This module wraps the existing command-line pipeline components without
removing them. FastAPI starts runs in a background thread, while Streamlit polls
the JSON state exposed through API endpoints.
"""
from __future__ import annotations

import json
import logging
import shutil
import threading
import time
import traceback
import uuid
import argparse
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

from config import settings
from domain.pipeline import PIPELINE_STAGE_DEFINITIONS
from feature_store.engineer import FeatureEngineer
from infrastructure.storage.pipeline_state import PipelineStateFileRepository
from ml.train import ModelTrainer
from prediction.service import PredictionService
from processing.local_processor import LocalProcessor
from scripts.generate_market_intel_dataset import generate_market_intel_datasets

logger = logging.getLogger(__name__)

try:
    from db import repositories as db_repo
except Exception:  # pragma: no cover - DB support is optional at runtime
    db_repo = None

RUNS_FILE = Path(settings.STATE_DIR) / "pipeline_runs.json"
CURRENT_FILE = Path(settings.STATE_DIR) / "pipeline_current.json"

STAGE_DEFINITIONS = list(PIPELINE_STAGE_DEFINITIONS)

TRANSFORMATION_RULES = {
    "encoding": ["trend_label", "sentiment", "risk_indicator"],
    "scaling": ["technology_popularity_score", "ecosystem_momentum_score"],
    "normalization": ["trend_score_avg", "sentiment_score_avg"],
    "aggregation": [
        "mentions",
        "job_postings",
        "github_event_count",
        "community_engagement_sum",
        "funding_amount_musd",
    ],
    "rolling average": ["mentions_7d_mean", "mentions_30d_mean", "salary_7d_mean"],
    "lag feature": ["mentions_7d_prev", "mentions_30d_prev"],
    "date/time extraction": ["date", "timestamp"],
    "percentage change": ["mentions_growth_pct", "salary_growth_pct", "popularity_growth_signal_avg"],
    "trend indicators": ["mentions_spike", "mentions_velocity", "ecosystem_momentum_score"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duration_seconds(start: Optional[str], end: Optional[str] = None) -> Optional[float]:
    if not start:
        return None
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end or _now())
        return round((end_dt - start_dt).total_seconds(), 3)
    except Exception:
        return None


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def _empty_stage(stage_id: str, name: str) -> Dict[str, Any]:
    return {
        "id": stage_id,
        "name": name,
        "status": "Pending",
        "progress": 0,
        "start_time": None,
        "end_time": None,
        "duration_seconds": None,
        "records_processed": 0,
        "records_inserted": 0,
        "records_rejected": 0,
        "duplicates_removed": 0,
        "missing_values_found": 0,
        "missing_values_handled": 0,
        "outliers_detected": 0,
        "input_shape": None,
        "output_shape": None,
        "error_details": None,
        "metadata": {},
    }


class PipelineStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._files = PipelineStateFileRepository(settings.STATE_DIR)

    def _read_runs_unlocked(self) -> List[Dict[str, Any]]:
        return self._files.read_runs()

    def list_runs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._read_runs_unlocked()

    def get_current(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._files.read_current()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for run in self._read_runs_unlocked():
                if run.get("run_id") == run_id:
                    return run
            current = self._files.read_current()
            if current and current.get("run_id") == run_id:
                return current
            return None

    def save_current(self, run: Dict[str, Any]) -> None:
        with self._lock:
            self._files.write_current(_jsonable(run))

    def append_history(self, run: Dict[str, Any]) -> None:
        with self._lock:
            runs = self._read_runs_unlocked()
            runs = [r for r in runs if r.get("run_id") != run.get("run_id")]
            runs.insert(0, _jsonable(run))
            self._files.write_runs(runs[:100])
            self._files.write_current(_jsonable(run))

    def is_running(self) -> bool:
        current = self.get_current()
        return bool(current and current.get("status") == "Running")

    def last_successful_run(self, exclude_run_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        for run in self.list_runs():
            if exclude_run_id and run.get("run_id") == exclude_run_id:
                continue
            if run.get("status") == "Completed":
                return run
        return None


STORE = PipelineStore()


class PipelineRunError(RuntimeError):
    pass


class PipelineRunner:
    def __init__(self, store: PipelineStore | None = None) -> None:
        self.store = store or STORE
        self._thread: Optional[threading.Thread] = None

    def start(
        self,
        trigger_type: str = "Full",
        triggered_by: str = "ui",
        clean: bool = True,
        regenerate_data: bool = False,
        min_rows: int = 100000,
        scale: float = 1.0,
        seed: int = 20260526,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if self.store.is_running():
            raise PipelineRunError("A pipeline run is already in progress.")

        run = self._new_run(
            trigger_type=trigger_type,
            triggered_by=triggered_by,
            clean=clean,
            regenerate_data=regenerate_data,
            min_rows=min_rows,
            scale=scale,
            seed=seed,
            formats=formats or ["csv", "parquet", "ndjson", "es"],
        )
        if db_repo is not None:
            db_id = db_repo.create_pipeline_run(run)
            if db_id:
                run["db_id"] = db_id
            if clean and getattr(settings, "CLEAN_DB_LATEST_ONLY", False):
                db_repo.cleanup_derived_rows_for_run(run["run_id"])
        self.store.save_current(run)
        self._thread = threading.Thread(target=self._execute, args=(run,), daemon=True)
        self._thread.start()
        return run

    def _new_run(self, **params: Any) -> Dict[str, Any]:
        run_id = f"run-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        return {
            "run_id": run_id,
            "triggered_by": params["triggered_by"],
            "trigger_type": params["trigger_type"],
            "status": "Running",
            "overall_progress": 0,
            "current_stage": None,
            "start_time": _now(),
            "end_time": None,
            "duration_seconds": None,
            "records_processed": 0,
            "features_created": 0,
            "model_score": None,
            "error_message": None,
            "parameters": {
                "clean": params["clean"],
                "regenerate_data": params["regenerate_data"],
                "min_rows": params["min_rows"],
                "scale": params["scale"],
                "seed": params["seed"],
                "formats": params["formats"],
            },
            "stages": [_empty_stage(stage_id, name) for stage_id, name in STAGE_DEFINITIONS],
            "metrics": self._empty_metrics(),
            "feature_tracking": {},
            "ml_tracking": {},
            "dataset_dimensions": {},
            "logs": [],
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        return {
            "overall_pipeline_progress": 0,
            "current_running_stage": None,
            "total_records_processed": 0,
            "total_records_inserted": 0,
            "total_records_rejected": 0,
            "total_duplicate_records_removed": 0,
            "total_missing_values_found": 0,
            "total_missing_values_handled": 0,
            "total_outliers_detected": 0,
            "total_features_created": 0,
            "total_features_selected_applied": 0,
            "dataset_shape_before_processing": None,
            "dataset_shape_after_processing": None,
            "model_training_status": "Pending",
            "model_accuracy_score": None,
            "prediction_output_count": 0,
            "runtime_duration_seconds": None,
            "last_successful_run": None,
            "last_failed_run": None,
        }

    def _execute(self, run: Dict[str, Any]) -> None:
        try:
            self._record_prior_run_metrics(run)
            raw_profile = self._stage_raw_data_collection(run)
            validation_profile = self._stage_data_validation(run, raw_profile)
            cleaning_profile = self._stage_data_cleaning(run, validation_profile)
            processing_result = self._stage_data_normalization(run, cleaning_profile)
            features_df = self._stage_feature_engineering(run, processing_result)
            selection = self._stage_feature_selection(run, features_df)
            split = self._stage_train_test_split(run, selection)
            training = self._stage_model_training(run, split)
            evaluation = self._stage_model_evaluation(run, training)
            predictions = self._stage_prediction_generation(run, evaluation)
            self._stage_final_output_creation(run, predictions)
            self._stage_dashboard_refresh(run)
            self._finish_run(run, "Completed")
        except Exception as exc:
            logger.exception("Pipeline run failed")
            self._fail_current_stage(run, exc)
            run["error_message"] = str(exc)
            self._finish_run(run, "Failed")

    def _record_prior_run_metrics(self, run: Dict[str, Any]) -> None:
        runs = self.store.list_runs()
        last_success = next((r for r in runs if r.get("status") == "Completed"), None)
        last_failed = next((r for r in runs if r.get("status") == "Failed"), None)
        run["metrics"]["last_successful_run"] = self._history_brief(last_success)
        run["metrics"]["last_failed_run"] = self._history_brief(last_failed)
        self._save(run)

    def _history_brief(self, run: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not run:
            return None
        return {
            "run_id": run.get("run_id"),
            "start_time": run.get("start_time"),
            "end_time": run.get("end_time"),
            "duration_seconds": run.get("duration_seconds"),
            "model_score": run.get("model_score"),
        }

    def _stage_raw_data_collection(self, run: Dict[str, Any]) -> Dict[str, Any]:
        stage = self._start_stage(run, "raw_data_collection")
        params = run["parameters"]
        if params.get("regenerate_data"):
            self._log(run, "Regenerating market-aware synthetic data.")
            generation = generate_market_intel_datasets(
                min_rows=int(params["min_rows"]),
                scale=float(params["scale"]),
                seed=int(params["seed"]),
                formats=list(params["formats"]),
            )
            stage["metadata"]["generation"] = generation

        profile = self._scan_csv_datasets()
        stage["records_processed"] = profile["event_rows"]
        stage["input_shape"] = profile["raw_shape"]
        stage["output_shape"] = profile["raw_shape"]
        stage["metadata"]["datasets"] = profile["datasets"]
        run["dataset_dimensions"]["raw"] = profile["raw_shape"]
        run["metrics"]["dataset_shape_before_processing"] = profile["raw_shape"]
        self._complete_stage(run, "raw_data_collection", progress=100)
        return profile

    def _stage_data_validation(self, run: Dict[str, Any], raw_profile: Dict[str, Any]) -> Dict[str, Any]:
        stage = self._start_stage(run, "data_validation")
        validation = self._validate_csv_datasets(raw_profile["datasets"])
        stage["records_processed"] = raw_profile["event_rows"]
        stage["records_rejected"] = validation["required_missing_rows"]
        stage["duplicates_removed"] = validation["duplicate_rows"]
        stage["missing_values_found"] = validation["missing_values_found"]
        stage["outliers_detected"] = validation["outliers_detected"]
        stage["input_shape"] = raw_profile["raw_shape"]
        stage["output_shape"] = raw_profile["raw_shape"]
        stage["metadata"]["dataset_profiles"] = validation["dataset_profiles"]
        run["metrics"]["total_records_rejected"] += validation["required_missing_rows"]
        run["metrics"]["total_duplicate_records_removed"] += validation["duplicate_rows"]
        run["metrics"]["total_missing_values_found"] += validation["missing_values_found"]
        run["metrics"]["total_outliers_detected"] += validation["outliers_detected"]
        run["metrics"]["total_records_processed"] = raw_profile["event_rows"]
        self._complete_stage(run, "data_validation", progress=100)
        return {**raw_profile, **validation}

    def _stage_data_cleaning(self, run: Dict[str, Any], validation_profile: Dict[str, Any]) -> Dict[str, Any]:
        stage = self._start_stage(run, "data_cleaning")
        cleaned_rows = max(
            validation_profile["event_rows"]
            - validation_profile["duplicate_rows"]
            - validation_profile["required_missing_rows"],
            0,
        )
        cleaned_shape = [int(cleaned_rows), int(validation_profile["raw_shape"][1])]
        stage["records_processed"] = validation_profile["event_rows"]
        stage["records_rejected"] = validation_profile["required_missing_rows"]
        stage["duplicates_removed"] = validation_profile["duplicate_rows"]
        stage["missing_values_found"] = validation_profile["missing_values_found"]
        stage["missing_values_handled"] = validation_profile["missing_values_found"]
        stage["input_shape"] = validation_profile["raw_shape"]
        stage["output_shape"] = cleaned_shape
        stage["metadata"]["cleaning_actions"] = [
            "drop rows missing required id/timestamp fields",
            "drop duplicate ids or duplicate trend-key observations",
            "standardize nulls before normalization",
        ]
        run["metrics"]["total_missing_values_handled"] += validation_profile["missing_values_found"]
        run["dataset_dimensions"]["cleaned"] = cleaned_shape
        self._complete_stage(run, "data_cleaning", progress=100)
        return {**validation_profile, "cleaned_shape": cleaned_shape, "cleaned_rows": cleaned_rows}

    def _stage_data_normalization(self, run: Dict[str, Any], cleaning_profile: Dict[str, Any]) -> Dict[str, Any]:
        stage = self._start_stage(run, "data_normalization_scaling")
        if run["parameters"].get("clean"):
            self._clean_local_outputs()
        processor = LocalProcessor(Path(settings.BASE_DIR) / "Data", run_id=run["run_id"])
        results = processor.run_all()
        sources = [source for source in processor.EVENT_SOURCES if results.get(source, 0) > 0]
        total_rows = int(results.get("total_event_rows", sum(results.get(source, 0) for source in sources)))
        processed_shape = [total_rows, 8]
        stage["records_processed"] = cleaning_profile["event_rows"]
        stage["records_inserted"] = total_rows
        stage["input_shape"] = cleaning_profile["cleaned_shape"]
        stage["output_shape"] = processed_shape
        stage["metadata"]["source_results"] = results
        stage["metadata"]["sources"] = sources
        run["metrics"]["total_records_inserted"] += total_rows
        run["metrics"]["dataset_shape_after_processing"] = processed_shape
        run["dataset_dimensions"]["normalized"] = processed_shape
        self._complete_stage(run, "data_normalization_scaling", progress=100)
        return {"processor_results": results, "sources": sources, "processed_shape": processed_shape}

    def _stage_feature_engineering(self, run: Dict[str, Any], processing_result: Dict[str, Any]) -> pd.DataFrame:
        stage = self._start_stage(run, "feature_engineering")
        feature_engineer = FeatureEngineer()
        features_df = feature_engineer.generate_daily_features(
            sources=processing_result["sources"],
            write_partitions=False,
            run_id=run["run_id"],
        )
        feature_shape = [int(features_df.shape[0]), int(features_df.shape[1])] if not features_df.empty else [0, 0]
        original_columns = self._raw_column_names()
        created_features = [c for c in features_df.columns if c not in {"timestamp", "date", "tech", "techs"}]
        stage["records_processed"] = int(processing_result["processed_shape"][0])
        stage["input_shape"] = processing_result["processed_shape"]
        stage["output_shape"] = feature_shape
        stage["metadata"]["created_feature_names"] = created_features
        stage["metadata"]["transformation_summary"] = self._transformation_summary(created_features)
        run["metrics"]["total_features_created"] = len(created_features)
        run["features_created"] = len(created_features)
        run["dataset_dimensions"]["feature_engineered"] = feature_shape
        run["feature_tracking"] = {
            "original_column_count": len(original_columns),
            "original_columns": original_columns,
            "new_feature_count": len(created_features),
            "created_features": created_features,
            "transformation_summary": stage["metadata"]["transformation_summary"],
        }
        self._complete_stage(run, "feature_engineering", progress=100)
        return features_df

    def _stage_feature_selection(self, run: Dict[str, Any], features_df: pd.DataFrame) -> Dict[str, Any]:
        stage = self._start_stage(run, "feature_selection")
        trainer = ModelTrainer()
        dataset = trainer.build_dataset()
        exclude = {"tech", "date", "timestamp", "future_score", "future_growth_pct", "trend_label"}
        feature_cols = [c for c in dataset.columns if c not in exclude and is_numeric_dtype(dataset[c])] if not dataset.empty else []
        dropped = []
        if not dataset.empty:
            for column in dataset.columns:
                if column in feature_cols:
                    continue
                reason = "target_or_metadata" if column in exclude else "non_numeric_or_unusable"
                dropped.append({"feature": column, "reason": reason})
        feature_profile = self._feature_profile(dataset, feature_cols)
        correlation = self._correlation_insights(dataset, feature_cols)
        stage["records_processed"] = int(len(features_df))
        stage["input_shape"] = [int(features_df.shape[0]), int(features_df.shape[1])] if not features_df.empty else [0, 0]
        stage["output_shape"] = [int(dataset.shape[0]), int(len(feature_cols))] if not dataset.empty else [0, 0]
        stage["metadata"]["features_used"] = feature_cols
        stage["metadata"]["features_dropped"] = dropped
        stage["metadata"]["correlation_insights"] = correlation
        run["feature_tracking"].update(
            {
                "features_used_count": len(feature_cols),
                "features_used": feature_cols,
                "features_dropped_count": len(dropped),
                "features_dropped": dropped,
                "null_percentage_per_feature": feature_profile["null_percentage_per_feature"],
                "data_type_per_feature": feature_profile["data_type_per_feature"],
                "correlation_insights": correlation,
            }
        )
        run["metrics"]["total_features_selected_applied"] = len(feature_cols)
        self._complete_stage(run, "feature_selection", progress=100)
        return {"trainer": trainer, "dataset": dataset, "feature_cols": feature_cols, "dropped": dropped}

    def _stage_train_test_split(self, run: Dict[str, Any], selection: Dict[str, Any]) -> Dict[str, Any]:
        stage = self._start_stage(run, "train_test_split")
        dataset = selection["dataset"]
        feature_cols = selection["feature_cols"]
        if dataset.empty or not feature_cols:
            raise RuntimeError("No training dataset/features available.")
        sorted_df = dataset.sort_values(["date", "tech"]).reset_index(drop=True)
        cutoff = int(len(sorted_df) * 0.8)
        cutoff = max(1, min(cutoff, len(sorted_df) - 1))
        train_shape = [int(cutoff), int(len(feature_cols))]
        test_shape = [int(len(sorted_df) - cutoff), int(len(feature_cols))]
        stage["records_processed"] = int(len(sorted_df))
        stage["input_shape"] = [int(sorted_df.shape[0]), int(sorted_df.shape[1])]
        stage["output_shape"] = train_shape
        stage["metadata"]["training_shape"] = train_shape
        stage["metadata"]["testing_shape"] = test_shape
        stage["metadata"]["split_strategy"] = "time-aware oldest 80 percent train, newest 20 percent test"
        run["dataset_dimensions"]["training"] = train_shape
        run["dataset_dimensions"]["testing"] = test_shape
        self._complete_stage(run, "train_test_split", progress=100)
        return {**selection, "training_shape": train_shape, "testing_shape": test_shape}

    def _stage_model_training(self, run: Dict[str, Any], split: Dict[str, Any]) -> Dict[str, Any]:
        stage = self._start_stage(run, "model_training")
        run["metrics"]["model_training_status"] = "Running"
        self._save(run)
        training_summary = split["trainer"].train(run_id=run["run_id"])
        if not training_summary:
            raise RuntimeError("Model training did not produce an artifact.")
        stage["records_processed"] = int(training_summary.get("training_rows", 0))
        stage["input_shape"] = training_summary.get("training_shape")
        stage["output_shape"] = [1, int(training_summary.get("feature_count", 0))]
        stage["metadata"].update(training_summary)
        run["ml_tracking"] = {
            "model_used": training_summary.get("model_used"),
            "training_start_time": stage["start_time"],
            "training_end_time": _now(),
            "training_dataset_size": training_summary.get("training_rows"),
            "testing_dataset_size": training_summary.get("testing_rows"),
            "features_used": training_summary.get("feature_columns", []),
            "target_variable": training_summary.get("target_variable"),
            "model_version": training_summary.get("training_timestamp"),
            "model_file_path": training_summary.get("model_path"),
            "last_trained_date": training_summary.get("training_timestamp"),
            "evaluation_metrics": training_summary.get("results", {}),
        }
        run["metrics"]["model_training_status"] = "Completed"
        self._complete_stage(run, "model_training", progress=100)
        return training_summary

    def _stage_model_evaluation(self, run: Dict[str, Any], training: Dict[str, Any]) -> Dict[str, Any]:
        stage = self._start_stage(run, "model_evaluation")
        results = training.get("results", {})
        accuracy = (
            results.get("random_forest_holdout", {})
            .get("report", {})
            .get("accuracy")
        )
        regression = results.get("random_forest_regressor_holdout", {})
        previous = self.store.last_successful_run(exclude_run_id=run["run_id"])
        previous_score = previous.get("model_score") if previous else None
        improved = None if previous_score is None or accuracy is None else float(accuracy) > float(previous_score)
        stage["records_processed"] = int(training.get("testing_rows", 0))
        stage["input_shape"] = training.get("testing_shape")
        stage["output_shape"] = [1, 4]
        stage["metadata"]["accuracy"] = accuracy
        stage["metadata"]["regression"] = regression
        stage["metadata"]["model_improved_vs_previous_run"] = improved
        run["model_score"] = accuracy
        run["metrics"]["model_accuracy_score"] = accuracy
        run["ml_tracking"]["evaluation_metrics"] = results
        run["ml_tracking"]["accuracy"] = accuracy
        run["ml_tracking"]["mae"] = regression.get("mae")
        run["ml_tracking"]["r2"] = regression.get("r2")
        run["ml_tracking"]["model_improved_vs_previous_run"] = improved
        self._complete_stage(run, "model_evaluation", progress=100)
        return training

    def _stage_prediction_generation(self, run: Dict[str, Any], training: Dict[str, Any]) -> Dict[str, Any]:
        stage = self._start_stage(run, "prediction_generation")
        predictions = self._generate_predictions(
            run_id=run["run_id"],
            model_id=training.get("db_model_id"),
        )
        stage["records_processed"] = predictions["prediction_count"]
        stage["input_shape"] = predictions["input_shape"]
        stage["output_shape"] = predictions["output_shape"]
        stage["metadata"]["prediction_path"] = predictions["prediction_path"]
        run["metrics"]["prediction_output_count"] = predictions["prediction_count"]
        run["dataset_dimensions"]["prediction"] = predictions["output_shape"]
        run["ml_tracking"]["prediction_count"] = predictions["prediction_count"]
        self._complete_stage(run, "prediction_generation", progress=100)
        return predictions

    def _stage_final_output_creation(self, run: Dict[str, Any], predictions: Dict[str, Any]) -> None:
        stage = self._start_stage(run, "final_output_creation")
        summary_path = Path(settings.FEATURE_STORE_DIR) / "pipeline_summary_latest.json"
        summary = {
            "run_id": run["run_id"],
            "status": run["status"],
            "created_at": _now(),
            "dataset_dimensions": run["dataset_dimensions"],
            "metrics": run["metrics"],
            "prediction_path": predictions["prediction_path"],
        }
        summary_path.write_text(json.dumps(_jsonable(summary), indent=2), encoding="utf-8")
        stage["records_processed"] = int(predictions["prediction_count"])
        stage["input_shape"] = predictions["output_shape"]
        stage["output_shape"] = predictions["output_shape"]
        stage["metadata"]["summary_path"] = str(summary_path)
        run["dataset_dimensions"]["final_output"] = predictions["output_shape"]
        self._complete_stage(run, "final_output_creation", progress=100)

    def _stage_dashboard_refresh(self, run: Dict[str, Any]) -> None:
        stage = self._start_stage(run, "dashboard_refresh")
        stage["metadata"]["message"] = "Feature and model files refreshed. Dashboard/API will reload by file mtime."
        stage["records_processed"] = run["metrics"]["prediction_output_count"]
        stage["input_shape"] = run["dataset_dimensions"].get("final_output")
        stage["output_shape"] = run["dataset_dimensions"].get("final_output")
        self._complete_stage(run, "dashboard_refresh", progress=100)

    def _scan_csv_datasets(self) -> Dict[str, Any]:
        data_dir = Path(settings.BASE_DIR) / "Data"
        configs = list(LocalProcessor.DATASET_CONFIGS)
        datasets: List[Dict[str, Any]] = []
        total_rows = 0
        total_cols = 0
        for config in configs:
            path = data_dir / config["path"]
            if not path.exists():
                continue
            header = pd.read_csv(path, nrows=0)
            rows = max(sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore")) - 1, 0)
            total_rows += rows
            total_cols += len(header.columns)
            datasets.append(
                {
                    "name": config["source"],
                    "path": str(path),
                    "rows": int(rows),
                    "columns": int(len(header.columns)),
                    "shape": [int(rows), int(len(header.columns))],
                    "id_col": config.get("id_col"),
                    "timestamp_col": config.get("timestamp_col"),
                    "topic_cols": list(config.get("topic_cols") or []),
                    "dedupe_cols": list(config.get("dedupe_cols") or ([config.get("id_col")] if config.get("id_col") else [])),
                }
            )
        market_events_path = data_dir / "market_intel" / "market_events.csv"
        if market_events_path.exists():
            header = pd.read_csv(market_events_path, nrows=0)
            rows = max(sum(1 for _ in market_events_path.open("r", encoding="utf-8", errors="ignore")) - 1, 0)
            total_rows += rows
            total_cols += len(header.columns)
            datasets.append(
                {
                    "name": "market_events",
                    "path": str(market_events_path),
                    "rows": int(rows),
                    "columns": int(len(header.columns)),
                    "shape": [int(rows), int(len(header.columns))],
                    "id_col": "event_id",
                    "timestamp_col": "event_date",
                    "topic_cols": ["topic_impacts"],
                    "dedupe_cols": ["event_id"],
                }
            )
        return {"datasets": datasets, "event_rows": int(total_rows), "raw_shape": [int(total_rows), int(total_cols)]}

    def _validate_csv_datasets(self, datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_missing = 0
        total_duplicates = 0
        total_required_missing = 0
        total_outliers = 0
        profiles = []
        for item in datasets:
            path = Path(item["path"])
            df = pd.read_csv(path, keep_default_na=True)
            missing = int(df.isna().sum().sum())
            dedupe_cols = [c for c in item.get("dedupe_cols", []) if c and c in df.columns]
            duplicates = int(df.duplicated(subset=dedupe_cols).sum()) if dedupe_cols else int(df.duplicated().sum())
            required_cols = [c for c in [item.get("id_col"), item.get("timestamp_col")] if c and c in df.columns]
            required_missing = int(df[required_cols].isna().any(axis=1).sum()) if required_cols else 0
            outliers = self._outlier_count(df)
            total_missing += missing
            total_duplicates += duplicates
            total_required_missing += required_missing
            total_outliers += outliers
            profiles.append(
                {
                    "dataset": item["name"],
                    "shape": [int(df.shape[0]), int(df.shape[1])],
                    "missing_values": missing,
                    "duplicate_rows": duplicates,
                    "required_missing_rows": required_missing,
                    "outliers_detected": outliers,
                    "null_percentage_per_column": {
                        str(col): round(float(df[col].isna().mean() * 100), 4) for col in df.columns
                    },
                    "data_type_per_column": {str(col): str(dtype) for col, dtype in df.dtypes.items()},
                }
            )
        return {
            "missing_values_found": int(total_missing),
            "duplicate_rows": int(total_duplicates),
            "required_missing_rows": int(total_required_missing),
            "outliers_detected": int(total_outliers),
            "dataset_profiles": profiles,
        }

    def _outlier_count(self, df: pd.DataFrame) -> int:
        count = 0
        for column in df.select_dtypes(include=[np.number]).columns:
            series = pd.to_numeric(df[column], errors="coerce").dropna()
            if len(series) < 4:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            count += int(((series < lower) | (series > upper)).sum())
        return count

    def _raw_column_names(self) -> List[str]:
        columns: set[str] = set()
        for item in self._scan_csv_datasets()["datasets"]:
            try:
                header = pd.read_csv(item["path"], nrows=0)
                columns.update(str(c) for c in header.columns)
            except Exception:
                continue
        return sorted(columns)

    def _transformation_summary(self, features: Iterable[str]) -> Dict[str, List[str]]:
        feature_set = set(features)
        summary: Dict[str, List[str]] = {}
        for transform, examples in TRANSFORMATION_RULES.items():
            matched = [f for f in feature_set if f in examples or any(token in f for token in examples)]
            if matched:
                summary[transform] = sorted(matched)[:25]
        return summary

    def _feature_profile(self, dataset: pd.DataFrame, feature_cols: List[str]) -> Dict[str, Any]:
        if dataset.empty:
            return {"null_percentage_per_feature": {}, "data_type_per_feature": {}}
        return {
            "null_percentage_per_feature": {
                col: round(float(dataset[col].isna().mean() * 100), 4) for col in feature_cols
            },
            "data_type_per_feature": {col: str(dataset[col].dtype) for col in feature_cols},
        }

    def _correlation_insights(self, dataset: pd.DataFrame, feature_cols: List[str]) -> List[Dict[str, Any]]:
        if dataset.empty or "future_growth_pct" not in dataset.columns or not feature_cols:
            return []
        correlations = []
        target = pd.to_numeric(dataset["future_growth_pct"], errors="coerce")
        for col in feature_cols:
            series = pd.to_numeric(dataset[col], errors="coerce")
            if series.nunique(dropna=True) <= 1:
                continue
            corr = series.corr(target)
            if pd.notna(corr):
                correlations.append({"feature": col, "target": "future_growth_pct", "correlation": round(float(corr), 5)})
        return sorted(correlations, key=lambda r: abs(r["correlation"]), reverse=True)[:20]

    def _generate_predictions(self, run_id: str | None = None, model_id: str | None = None) -> Dict[str, Any]:
        return PredictionService().generate_latest_predictions(run_id=run_id, model_id=model_id).as_dict()

    def _clean_local_outputs(self) -> None:
        targets = [
            Path(settings.PROCESSED_DIR),
            Path(settings.FEATURE_STORE_DIR) / "features",
            Path(settings.FEATURE_STORE_DIR) / "features_all.parquet",
            Path(settings.FEATURE_STORE_DIR) / "feature_index.json",
            Path(settings.FEATURE_STORE_DIR) / "predictions_latest.parquet",
            Path(settings.FEATURE_STORE_DIR) / "predictions_latest.json",
            Path(settings.FEATURE_STORE_DIR) / "pipeline_summary_latest.json",
        ]
        for target in targets:
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        Path(settings.PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.FEATURE_STORE_DIR).mkdir(parents=True, exist_ok=True)

    def _start_stage(self, run: Dict[str, Any], stage_id: str) -> Dict[str, Any]:
        stage = self._find_stage(run, stage_id)
        stage["status"] = "Running"
        stage["progress"] = 0
        stage["start_time"] = _now()
        stage["end_time"] = None
        run["current_stage"] = stage["name"]
        run["metrics"]["current_running_stage"] = stage["name"]
        self._log(run, f"Started stage: {stage['name']}")
        self._update_overall_progress(run)
        self._save(run)
        self._persist_stage(run, stage)
        return stage

    def _complete_stage(self, run: Dict[str, Any], stage_id: str, progress: int = 100) -> None:
        stage = self._find_stage(run, stage_id)
        stage["status"] = "Completed"
        stage["progress"] = progress
        stage["end_time"] = _now()
        stage["duration_seconds"] = _duration_seconds(stage["start_time"], stage["end_time"])
        self._log(run, f"Completed stage: {stage['name']}")
        self._update_overall_progress(run)
        self._save(run)
        self._persist_stage(run, stage)

    def _fail_current_stage(self, run: Dict[str, Any], exc: Exception) -> None:
        for stage in run["stages"]:
            if stage["status"] == "Running":
                stage["status"] = "Failed"
                stage["progress"] = stage.get("progress", 0)
                stage["end_time"] = _now()
                stage["duration_seconds"] = _duration_seconds(stage["start_time"], stage["end_time"])
                stage["error_details"] = {
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
                break
        self._log(run, f"Pipeline failed: {exc}", level="ERROR")
        self._update_overall_progress(run)
        self._save(run)
        for stage in run["stages"]:
            if stage["status"] == "Failed":
                self._persist_stage(run, stage)
                break

    def _find_stage(self, run: Dict[str, Any], stage_id: str) -> Dict[str, Any]:
        for stage in run["stages"]:
            if stage["id"] == stage_id:
                return stage
        raise KeyError(stage_id)

    def _update_overall_progress(self, run: Dict[str, Any]) -> None:
        total = len(run["stages"]) * 100
        completed = sum(int(stage.get("progress", 0)) for stage in run["stages"])
        progress = int(round((completed / total) * 100)) if total else 0
        run["overall_progress"] = progress
        run["metrics"]["overall_pipeline_progress"] = progress
        run["metrics"]["runtime_duration_seconds"] = _duration_seconds(run["start_time"])
        run["duration_seconds"] = run["metrics"]["runtime_duration_seconds"]

    def _finish_run(self, run: Dict[str, Any], status: str) -> None:
        run["status"] = status
        run["end_time"] = _now()
        run["duration_seconds"] = _duration_seconds(run["start_time"], run["end_time"])
        run["records_processed"] = run["metrics"].get("total_records_processed", 0)
        run["features_created"] = run["metrics"].get("total_features_created", 0)
        run["model_score"] = run["metrics"].get("model_accuracy_score")
        run["metrics"]["runtime_duration_seconds"] = run["duration_seconds"]
        if status == "Completed":
            run["overall_progress"] = 100
            run["metrics"]["overall_pipeline_progress"] = 100
            run["current_stage"] = None
            run["metrics"]["current_running_stage"] = None
        self.store.append_history(run)
        self._persist_run(run)

    def _log(self, run: Dict[str, Any], message: str, level: str = "INFO") -> None:
        run["logs"].append({"time": _now(), "level": level, "message": message})
        run["logs"] = run["logs"][-500:]

    def _save(self, run: Dict[str, Any]) -> None:
        self.store.save_current(run)
        self._persist_run(run)

    def _persist_run(self, run: Dict[str, Any]) -> None:
        if db_repo is not None:
            db_repo.update_pipeline_run(run)

    def _persist_stage(self, run: Dict[str, Any], stage: Dict[str, Any]) -> None:
        if db_repo is None:
            return
        stage_order = next(
            (idx for idx, (stage_id, _) in enumerate(STAGE_DEFINITIONS, start=1) if stage_id == stage.get("id")),
            0,
        )
        db_repo.upsert_pipeline_stage(run["run_id"], stage, stage_order)


RUNNER = PipelineRunner()


def get_runner() -> PipelineRunner:
    return RUNNER


def get_store() -> PipelineStore:
    return STORE


def main() -> None:
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(levelname)s:%(name)s:%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--triggered-by", default="cli")
    parser.add_argument("--trigger-type", default="Full")
    parser.add_argument("--clean", action="store_true", default=True)
    parser.add_argument("--no-clean", action="store_false", dest="clean")
    parser.add_argument("--regenerate-data", action="store_true")
    parser.add_argument("--min-rows", type=int, default=100000)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=20260526)
    parser.add_argument("--formats", nargs="+", default=["csv", "parquet", "ndjson", "es"])
    args = parser.parse_args()

    run = RUNNER.start(
        trigger_type=args.trigger_type,
        triggered_by=args.triggered_by,
        clean=args.clean,
        regenerate_data=args.regenerate_data,
        min_rows=args.min_rows,
        scale=args.scale,
        seed=args.seed,
        formats=args.formats,
    )
    logger.info("Started pipeline run %s", run["run_id"])
    while RUNNER._thread and RUNNER._thread.is_alive():
        time.sleep(1)
    final = STORE.get_run(run["run_id"]) or run
    logger.info("Pipeline run %s finished with status %s", run["run_id"], final.get("status"))
    if final.get("status") == "Failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
