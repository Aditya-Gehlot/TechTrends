from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from config import settings
from pipeline.runner import PipelineRunError, get_runner, get_store

app = FastAPI(title="Tech Trends Intelligence API")
logger = logging.getLogger(__name__)

_FEATURE_CACHE: Dict[str, Any] = {"path": None, "mtime": None, "df": None}

try:
    from db import repositories as db_repo
except Exception:  # pragma: no cover - DB support is optional at runtime
    db_repo = None


class TrendResponse(BaseModel):
    technology: str
    predicted_growth: Optional[float]
    confidence: Optional[float]
    trend: Optional[str]
    features: Optional[Dict[str, Any]]
    feature_importances: Optional[Dict[str, float]] = None


class PipelineRunRequest(BaseModel):
    trigger_type: str = "Full"
    triggered_by: str = "ui"
    clean: bool = True
    regenerate_data: bool = False
    min_rows: int = 100000
    scale: float = 1.0
    seed: int = 20260526
    formats: list[str] = Field(default_factory=lambda: ["csv", "parquet", "ndjson", "es"])


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def _load_latest_model() -> Optional[Any]:
    if db_repo is not None:
        db_model = db_repo.get_latest_model()
        if db_model and db_model.get("artifact_path"):
            path = Path(db_model["artifact_path"])
            if path.exists():
                try:
                    artifact = joblib.load(path)
                    if isinstance(artifact, dict):
                        artifact["artifact_path"] = str(path)
                        artifact["db_metadata"] = db_model
                        return artifact
                except Exception:
                    logger.exception("Failed to load DB-referenced model %s", path)

    model_dir = Path(settings.ML_MODELS_DIR)
    if not model_dir.exists():
        return None
    models = sorted(model_dir.glob("*.joblib"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not models:
        return None
    try:
        artifact = joblib.load(models[0])
        if isinstance(artifact, dict) and "model" in artifact:
            artifact["artifact_path"] = str(models[0])
            return artifact
        return {"model": artifact, "feature_columns": None, "trained_at": None, "artifact_path": str(models[0])}
    except Exception:
        logger.exception("Failed to load model %s", models[0])
        return None


def _load_features_all() -> pd.DataFrame:
    path = Path(settings.FEATURE_STORE_DIR) / "features_all.parquet"
    if not path.exists():
        return pd.DataFrame()

    mtime = path.stat().st_mtime
    if _FEATURE_CACHE["path"] == str(path) and _FEATURE_CACHE["mtime"] == mtime and _FEATURE_CACHE["df"] is not None:
        return _FEATURE_CACHE["df"].copy()

    try:
        df = pd.read_parquet(path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        _FEATURE_CACHE.update({"path": str(path), "mtime": mtime, "df": df})
        return df.copy()
    except Exception:
        logger.exception("Failed to read consolidated features %s", path)
        return pd.DataFrame()


def _latest_feature_for_tech(tech: str) -> Optional[Dict[str, Any]]:
    if db_repo is not None:
        db_feature = db_repo.get_latest_feature(tech)
        if db_feature:
            return db_feature

    df = _load_features_all()
    if not df.empty and "tech" in df.columns:
        wanted = tech.casefold()
        matches = df[df["tech"].astype(str).str.casefold() == wanted]
        if not matches.empty:
            sort_col = "timestamp" if "timestamp" in matches.columns else "date"
            row = matches.sort_values(sort_col).tail(1).iloc[0].to_dict()
            return _jsonable(row)

    # Backward-compatible fallback for older feature stores.
    base = Path(settings.FEATURE_STORE_DIR) / "features" / tech
    if not base.exists():
        return None
    files = sorted(base.glob("*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        df = pd.read_parquet(files[0])
        return _jsonable(df.iloc[0].to_dict())
    except Exception:
        logger.exception("Failed to read feature file %s", files[0])
        return None


def _feature_vector(features: Dict[str, Any], feature_columns: Optional[list[str]]) -> Optional[Any]:
    if feature_columns:
        values = []
        for column in feature_columns:
            value = features.get(column, 0.0)
            try:
                values.append(float(value if value is not None else 0.0))
            except Exception:
                values.append(0.0)
        return pd.DataFrame([values], columns=feature_columns)

    numeric_values = []
    for key, value in features.items():
        if key in {"date", "timestamp", "tech"}:
            continue
        try:
            numeric_values.append(float(value))
        except Exception:
            continue
    if not numeric_values:
        return None
    return np.array(numeric_values).reshape(1, -1)


@app.get("/health")
def health():
    features_path = Path(settings.FEATURE_STORE_DIR) / "features_all.parquet"
    model = _load_latest_model()
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "features_available": features_path.exists(),
        "model_available": model is not None,
    }


@app.post("/pipeline/run")
def pipeline_run(request: PipelineRunRequest):
    try:
        run = get_runner().start(
            trigger_type=request.trigger_type,
            triggered_by=request.triggered_by,
            clean=request.clean,
            regenerate_data=request.regenerate_data,
            min_rows=request.min_rows,
            scale=request.scale,
            seed=request.seed,
            formats=request.formats,
        )
        return {"accepted": True, "run_id": run["run_id"], "status": run["status"]}
    except PipelineRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/pipeline/status")
def pipeline_status():
    if db_repo is not None:
        db_run = db_repo.get_latest_run_detail()
        if db_run:
            return {"status": db_run.get("status", "Idle"), "run": db_run}

    current = get_store().get_current()
    if not current:
        return {"status": "Idle", "run": None}
    return {"status": current.get("status", "Idle"), "run": current}


@app.get("/pipeline/runs")
def pipeline_runs(limit: int = Query(25, ge=1, le=100)):
    if not isinstance(limit, int):
        limit = 25
    if db_repo is not None:
        db_runs = db_repo.list_pipeline_runs(limit=limit)
        if db_runs:
            return {"runs": db_runs}

    runs = get_store().list_runs()[:limit]
    rows = []
    for run in runs:
        rows.append(
            {
                "run_id": run.get("run_id"),
                "triggered_by": run.get("triggered_by"),
                "trigger_type": run.get("trigger_type"),
                "status": run.get("status"),
                "start_time": run.get("start_time"),
                "end_time": run.get("end_time"),
                "duration_seconds": run.get("duration_seconds"),
                "records_processed": run.get("metrics", {}).get("total_records_processed"),
                "features_created": run.get("features_created"),
                "model_score": run.get("model_score"),
                "error_message": run.get("error_message"),
            }
        )
    return {"runs": rows}


@app.get("/pipeline/runs/{run_id}")
def pipeline_run_detail(run_id: str):
    if db_repo is not None:
        db_run = db_repo.get_pipeline_run_detail(run_id)
        if db_run:
            return db_run

    run = get_store().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run


@app.get("/pipeline/runs/{run_id}/logs")
def pipeline_run_logs(run_id: str):
    run = get_store().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return {"run_id": run_id, "logs": run.get("logs", [])}


@app.get("/pipeline/metrics")
def pipeline_metrics():
    current = get_store().get_current()
    if not current:
        return {"metrics": {}, "feature_tracking": {}, "ml_tracking": {}, "dataset_dimensions": {}}
    return {
        "run_id": current.get("run_id"),
        "status": current.get("status"),
        "metrics": current.get("metrics", {}),
        "feature_tracking": current.get("feature_tracking", {}),
        "ml_tracking": current.get("ml_tracking", {}),
        "dataset_dimensions": current.get("dataset_dimensions", {}),
    }


@app.get("/pipeline/predictions/latest")
def pipeline_predictions_latest():
    if db_repo is not None:
        db_predictions = db_repo.get_latest_predictions()
        if db_predictions:
            return {"predictions": db_predictions}

    path = Path(settings.FEATURE_STORE_DIR) / "predictions_latest.json"
    if not path.exists():
        return {"predictions": []}
    try:
        return {"predictions": json.loads(path.read_text(encoding="utf-8"))}
    except Exception:
        logger.exception("Failed to read latest predictions")
        raise HTTPException(status_code=500, detail="Could not read latest predictions")


@app.get("/sources/summary")
def sources_summary():
    db_sources = db_repo.get_source_summary() if db_repo is not None else []
    summary_path = Path(settings.BASE_DIR) / "Data" / "dataset_summary.json"
    summary = {}
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to read dataset summary")

    df = _load_features_all()
    feature_summary = {
        "feature_rows": int(len(df)) if not df.empty else 0,
        "technologies": int(df["tech"].nunique()) if not df.empty and "tech" in df.columns else 0,
        "feature_min_date": _jsonable(df["date"].min()) if not df.empty and "date" in df.columns else None,
        "feature_max_date": _jsonable(df["date"].max()) if not df.empty and "date" in df.columns else None,
    }

    model = _load_latest_model()
    model_summary = {
        "model_available": model is not None,
        "trained_at": model.get("trained_at") if isinstance(model, dict) else None,
        "horizon_days": model.get("horizon_days") if isinstance(model, dict) else None,
        "artifact_path": model.get("artifact_path") if isinstance(model, dict) else None,
    }
    if db_sources:
        summary = {item["source"]: item["row_count"] for item in db_sources}
    return {"dataset": summary, "sources": db_sources, "features": feature_summary, "model": model_summary}


@app.get("/sources/market-context")
def sources_market_context():
    path = Path(settings.BASE_DIR) / "Data" / "market_intel" / "market_context_2026.json"
    if not path.exists():
        return {"context": None}
    try:
        return {"context": json.loads(path.read_text(encoding="utf-8"))}
    except Exception:
        logger.exception("Failed to read market context")
        raise HTTPException(status_code=500, detail="Could not read market context")


@app.get("/trends/top")
def trends_top(limit: int = Query(10, ge=1, le=100)):
    if db_repo is not None:
        db_rows = db_repo.get_top_trends(limit=limit)
        if db_rows:
            return {"top": db_rows}

    df = _load_features_all()
    if df.empty or "tech" not in df.columns:
        return {"top": []}

    sort_col = "timestamp" if "timestamp" in df.columns else "date"
    latest = df.sort_values(sort_col).groupby("tech", as_index=False).tail(1)
    rows = []
    for _, row in latest.iterrows():
        rows.append(
            {
                "tech": _jsonable(row.get("tech")),
                "score": float(row.get("technology_popularity_score") or 0.0),
                "momentum": float(row.get("ecosystem_momentum_score") or 0.0),
                "date": _jsonable(row.get("date")),
                "mentions_7d_mean": float(row.get("mentions_7d_mean") or 0.0),
                "trend_score_avg": float(row.get("trend_score_avg") or 0.0),
            }
        )
    rows = sorted(rows, key=lambda r: r["score"], reverse=True)[:limit]
    return {"top": rows}


@app.get("/trends/history/{name:path}")
def trends_history(name: str, limit: int = Query(120, ge=1, le=1000)):
    if db_repo is not None:
        db_history = db_repo.get_trend_history(name, limit=limit)
        if db_history:
            return {"technology": name, "history": db_history}

    df = _load_features_all()
    if df.empty or "tech" not in df.columns:
        raise HTTPException(status_code=404, detail="No feature history found")

    matches = df[df["tech"].astype(str).str.casefold() == name.casefold()]
    if matches.empty:
        raise HTTPException(status_code=404, detail="No feature history found for technology")

    sort_col = "timestamp" if "timestamp" in matches.columns else "date"
    matches = matches.sort_values(sort_col).tail(limit)
    keep = [
        "date",
        "tech",
        "technology_popularity_score",
        "ecosystem_momentum_score",
        "mentions",
        "mentions_7d_mean",
        "trend_score_avg",
        "sentiment_score_avg",
        "job_postings",
        "github_events",
        "community_engagement_sum",
        "funding_amount_musd",
    ]
    keep = [col for col in keep if col in matches.columns]
    return {"technology": name, "history": _jsonable(matches[keep].to_dict(orient="records"))}


@app.get("/features/{name:path}")
def features(name: str):
    feat = _latest_feature_for_tech(name)
    if not feat:
        raise HTTPException(status_code=404, detail="No features found for technology")
    return {"technology": name, "features": feat}


@app.get("/technology/{name:path}", response_model=Dict[str, Any])
def technology(name: str):
    feat = _latest_feature_for_tech(name)
    if not feat:
        raise HTTPException(status_code=404, detail="No features found for technology")
    return {"technology": name, "features": feat}


@app.get("/models/latest")
def models_latest():
    if db_repo is not None:
        db_model = db_repo.get_latest_model()
        if db_model:
            return db_model

    model = _load_latest_model()
    if model is None:
        raise HTTPException(status_code=404, detail="No model artifact found")
    return {
        "trained_at": model.get("trained_at"),
        "horizon_days": model.get("horizon_days"),
        "feature_columns": model.get("feature_columns"),
        "artifact_path": model.get("artifact_path"),
        "holdout_confidence": model.get("holdout_confidence"),
        "feature_importances": model.get("feature_importances"),
        "has_regression_model": model.get("regression_model") is not None,
    }


@app.get("/forecast/{name:path}", response_model=TrendResponse)
def forecast(name: str, horizon: int = Query(7, ge=1, le=90)):
    feat = _latest_feature_for_tech(name)
    artifact = _load_latest_model()
    if not feat:
        raise HTTPException(status_code=404, detail="No features found for technology")

    features = {k: v for k, v in feat.items() if k not in {"date", "timestamp", "tech"}}
    if artifact is None:
        return TrendResponse(technology=name, predicted_growth=None, confidence=None, trend=None, features=features)

    model = artifact.get("model")
    feature_columns = artifact.get("feature_columns")
    X_arr = _feature_vector(features, feature_columns)
    if X_arr is None:
        return TrendResponse(technology=name, predicted_growth=None, confidence=None, trend=None, features=features)

    try:
        pred = model.predict(X_arr)
        trend = str(pred[0] if hasattr(pred, "__len__") else pred)
        confidence = None
        if hasattr(model, "predict_proba"):
            try:
                confidence = float(model.predict_proba(X_arr).max())
            except Exception:
                confidence = None

        predicted_growth = None
        reg_model = artifact.get("regression_model") if isinstance(artifact, dict) else None
        if reg_model is not None:
            try:
                predicted_growth = float(reg_model.predict(X_arr)[0])
            except Exception:
                logger.exception("Regression prediction failed for %s", name)

        if predicted_growth is None:
            label_to_growth = {"booming": 0.25, "stable": 0.0, "declining": -0.15}
            predicted_growth = float(label_to_growth.get(trend, 0.0))

        return TrendResponse(
            technology=name,
            predicted_growth=predicted_growth,
            confidence=confidence,
            trend=trend,
            features=features,
            feature_importances=artifact.get("feature_importances") if isinstance(artifact, dict) else None,
        )
    except Exception:
        logger.exception("Prediction failed for %s", name)
        raise HTTPException(status_code=500, detail="Prediction failed")
