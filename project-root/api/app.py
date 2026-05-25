from __future__ import annotations

import glob
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import settings

app = FastAPI(title="Tech Trends Intelligence API")
logger = logging.getLogger(__name__)


class TrendResponse(BaseModel):
    technology: str
    predicted_growth: Optional[float]
    confidence: Optional[float]
    trend: Optional[str]
    features: Optional[Dict[str, Any]]
    feature_importances: Optional[Dict[str, float]] = None


def _load_latest_model() -> Optional[Any]:
    model_dir = Path(settings.ML_MODELS_DIR)
    if not model_dir.exists():
        return None
    models = sorted(model_dir.glob("*.joblib"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not models:
        return None
    try:
        artifact = joblib.load(models[0])
        # artifact expected to be a dict with keys: model, feature_columns, trained_at
        if isinstance(artifact, dict) and "model" in artifact:
            return artifact
        # backward compatibility: plain model
        return {"model": artifact, "feature_columns": None, "trained_at": None}
    except Exception:
        logger.exception("Failed to load model %s", models[0])
        return None


def _latest_feature_for_tech(tech: str) -> Optional[Dict[str, Any]]:
    base = Path(settings.FEATURE_STORE_DIR) / "features" / tech
    if not base.exists():
        return None
    files = sorted(base.glob("*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        df = pd.read_parquet(files[0])
        row = df.iloc[0].to_dict()
        return row
    except Exception:
        logger.exception("Failed to read feature file %s", files[0])
        return None


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/trends/top")
def trends_top(limit: int = 10):
    base = Path(settings.FEATURE_STORE_DIR) / "features"
    rows = []
    if not base.exists():
        return {"top": []}
    for tech_dir in base.iterdir():
        if not tech_dir.is_dir():
            continue
        files = sorted(tech_dir.glob("*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            continue
        try:
            df = pd.read_parquet(files[0])
            score = float(df.iloc[0].get("technology_popularity_score") or 0)
            rows.append({"tech": tech_dir.name, "score": score})
        except Exception:
            continue
    rows = sorted(rows, key=lambda r: r["score"], reverse=True)[:limit]
    return {"top": rows}


@app.get("/features/{name}")
def features(name: str):
    feat = _latest_feature_for_tech(name)
    if not feat:
        raise HTTPException(status_code=404, detail="No features found for technology")
    return {"technology": name, "features": feat}


@app.get("/technology/{name}", response_model=Dict[str, Any])
def technology(name: str):
    feat = _latest_feature_for_tech(name)
    if not feat:
        raise HTTPException(status_code=404, detail="No features found for technology")
    return {"technology": name, "features": feat}


@app.get("/forecast/{name}", response_model=TrendResponse)
def forecast(name: str, horizon: int = 7):
    feat = _latest_feature_for_tech(name)
    artifact = _load_latest_model()
    if not feat:
        raise HTTPException(status_code=404, detail="No features found for technology")
    features = {k: v for k, v in feat.items() if k not in ("date", "timestamp")}

    if artifact is None:
        return TrendResponse(technology=name, predicted_growth=None, confidence=None, trend=None, features=features)

    model = artifact.get("model")
    feature_columns = artifact.get("feature_columns")

    # build input vector using model's feature column list if available
    try:
        import numpy as np

        if feature_columns:
            vals = []
            for c in feature_columns:
                v = features.get(c)
                if v is None:
                    v = 0.0
                vals.append(float(v))
            X_arr = np.array(vals).reshape(1, -1)
        else:
            # fallback: use numeric features from latest feature file
            vals = [float(v) for k, v in features.items() if isinstance(v, (int, float))]
            if not vals:
                return TrendResponse(technology=name, predicted_growth=None, confidence=None, trend=None, features=features)
            X_arr = np.array(vals).reshape(1, -1)

        pred = model.predict(X_arr)
        proba = None
        try:
            proba_vals = model.predict_proba(X_arr)
            proba = float(proba_vals.max())
        except Exception:
            proba = None
        trend = pred[0] if hasattr(pred, "__len__") else str(pred)

        # map categorical label to an estimated growth percentage for UX
        label_to_growth = {"booming": 0.25, "stable": 0.0, "declining": -0.15}
        est_growth = None
        try:
            est_growth = float(label_to_growth.get(str(trend), 0.0))
        except Exception:
            est_growth = None

        # feature importances if available in artifact
        fi = None
        try:
            fi = artifact.get("feature_importances") if isinstance(artifact, dict) else None
        except Exception:
            fi = None

        # try to supplement with a Prophet numeric forecast if available
        numeric_forecast = None
        try:
            prophet_dir = Path(settings.ML_MODELS_DIR) / "prophet"
            if prophet_dir.exists():
                # attempt to find a prophet model for this tech
                candidates = list(prophet_dir.glob(f"prophet_{name}_*.joblib"))
                if candidates:
                    m = joblib.load(candidates[0])
                    future = m.make_future_dataframe(periods=horizon)
                    fc = m.predict(future)
                    # take first horizon mean change vs last observed
                    last_y = fc["yhat"].iloc[-horizon-1]
                    pred_y = fc["yhat"].iloc[-1]
                    numeric_forecast = float((pred_y - last_y) / (last_y if last_y else 1.0))
        except Exception:
            numeric_forecast = None

        # prefer numeric forecast when available
        final_growth = numeric_forecast if numeric_forecast is not None else est_growth

        return TrendResponse(
            technology=name,
            predicted_growth=final_growth,
            confidence=proba,
            trend=trend,
            features=features,
            feature_importances=fi,
        )
    except Exception:
        logger.exception("Prediction failed for %s", name)
        raise HTTPException(status_code=500, detail="Prediction failed")
