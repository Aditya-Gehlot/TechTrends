from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from config import settings

try:
    from db import repositories as db_repo
except Exception:  # pragma: no cover - DB is optional at runtime
    db_repo = None


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


@dataclass(frozen=True)
class PredictionGenerationResult:
    prediction_count: int
    input_shape: list[int]
    output_shape: list[int]
    prediction_path: str | None
    prediction_json_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "prediction_count": self.prediction_count,
            "input_shape": self.input_shape,
            "output_shape": self.output_shape,
            "prediction_path": self.prediction_path,
        }
        if self.prediction_json_path is not None:
            payload["prediction_json_path"] = self.prediction_json_path
        return payload


class PredictionService:
    """Generates latest per-technology predictions from feature/model artifacts."""

    def __init__(
        self,
        feature_store_dir: Path | str | None = None,
        model_dir: Path | str | None = None,
    ) -> None:
        self.feature_store_dir = Path(feature_store_dir or settings.FEATURE_STORE_DIR)
        self.model_dir = Path(model_dir or settings.ML_MODELS_DIR)

    def generate_latest_predictions(
        self,
        run_id: str | None = None,
        model_id: str | None = None,
    ) -> PredictionGenerationResult:
        feature_path = self.feature_store_dir / "features_all.parquet"
        model_files = sorted(self.model_dir.glob("*.joblib"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not feature_path.exists() or not model_files:
            return PredictionGenerationResult(
                prediction_count=0,
                input_shape=[0, 0],
                output_shape=[0, 0],
                prediction_path=None,
            )

        features = pd.read_parquet(feature_path)
        features["timestamp"] = pd.to_datetime(features["timestamp"], errors="coerce")
        latest = features.sort_values("timestamp").groupby("tech", as_index=False).tail(1).reset_index(drop=True)
        artifact = joblib.load(model_files[0])
        model = artifact.get("model")
        regression_model = artifact.get("regression_model")
        feature_columns = artifact.get("feature_columns") or []

        X = latest.reindex(columns=feature_columns).fillna(0)
        predictions = latest[["tech", "date", "technology_popularity_score", "ecosystem_momentum_score"]].copy()
        predictions["trend"] = model.predict(X) if model is not None and not X.empty else None
        if hasattr(model, "predict_proba") and not X.empty:
            predictions["confidence"] = np.max(model.predict_proba(X), axis=1)
        else:
            predictions["confidence"] = None
        if regression_model is not None and not X.empty:
            predictions["predicted_growth"] = regression_model.predict(X)
        else:
            predictions["predicted_growth"] = predictions["trend"].map(
                {"booming": 0.25, "stable": 0.0, "declining": -0.15}
            )

        out_path = self.feature_store_dir / "predictions_latest.parquet"
        json_path = self.feature_store_dir / "predictions_latest.json"
        predictions.to_parquet(out_path, index=False)
        json_path.write_text(json.dumps(_jsonable(predictions.to_dict(orient="records")), indent=2), encoding="utf-8")
        if db_repo is not None:
            db_repo.insert_predictions_batch(predictions, external_run_id=run_id, model_id=model_id)

        return PredictionGenerationResult(
            prediction_count=int(len(predictions)),
            input_shape=[int(latest.shape[0]), int(latest.shape[1])],
            output_shape=[int(predictions.shape[0]), int(predictions.shape[1])],
            prediction_path=str(out_path),
            prediction_json_path=str(json_path),
        )
