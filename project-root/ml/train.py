"""ML training pipeline.

Loads features from the feature store, builds a time-aware training set,
trains classifiers and a growth regressor, evaluates and persists models and
artifacts under `ml/models/` and `ml/artifacts/`.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List

import joblib
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, confusion_matrix, mean_absolute_error, r2_score

try:
    from sklearn.model_selection import train_test_split
except Exception:
    train_test_split = None

try:
    import xgboost as xgb
except Exception:
    xgb = None

try:
    from prophet import Prophet
except Exception:
    Prophet = None

from config import settings

logger = logging.getLogger(__name__)

try:
    from db import repositories as db_repo
except Exception:  # pragma: no cover - DB support is optional at runtime
    db_repo = None


class ModelTrainer:
    def __init__(self, feature_dir: Path | None = None, model_dir: Path | None = None, artifacts_dir: Path | None = None):
        self.feature_dir = Path(feature_dir or settings.FEATURE_STORE_DIR) / "features"
        self.model_dir = Path(model_dir or settings.ML_MODELS_DIR)
        self.artifacts_dir = Path(artifacts_dir or (Path(settings.ML_MODELS_DIR).parents[0] / "artifacts"))
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _load_all_features(self) -> pd.DataFrame:
        parts = []
        consolidated_path = Path(self.feature_dir).parents[0] / "features_all.parquet"
        if consolidated_path.exists():
            try:
                df = pd.read_parquet(consolidated_path)
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"]).dt.date
                elif "timestamp" in df.columns:
                    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
                return df
            except Exception:
                logger.exception("Failed to read consolidated feature file %s", consolidated_path)

        if not self.feature_dir.exists():
            return pd.DataFrame()
        for tech_dir in self.feature_dir.iterdir():
            if not tech_dir.is_dir():
                continue
            for f in tech_dir.glob("*.parquet"):
                try:
                    df = pd.read_parquet(f)
                    df["tech"] = tech_dir.name
                    parts.append(df)
                except Exception:
                    logger.exception("Failed to read feature file %s", f)
        if not parts:
            return pd.DataFrame()
        df = pd.concat(parts, ignore_index=True)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        elif "timestamp" in df.columns:
            df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        return df

    def build_dataset(self, horizon_days: int = 7) -> pd.DataFrame:
        df = self._load_all_features()
        if df.empty:
            logger.info("No feature data found for training")
            return df

        # ensure score exists
        if "technology_popularity_score" not in df.columns:
            logger.info("No popularity score found in features; cannot build labels")
            return pd.DataFrame()

        rows = []
        for tech, g in df.groupby("tech"):
            g = g.sort_values("date").reset_index(drop=True)
            if len(g) < horizon_days + 1:
                continue
            g["future_score"] = g["technology_popularity_score"].shift(-horizon_days)
            g = g.dropna(subset=["future_score"]).copy()
            if g.empty:
                continue
            g["future_growth_pct"] = (
                g["future_score"] / (g["technology_popularity_score"].replace({0: np.nan})) - 1
            ).replace([np.inf, -np.inf], 0).fillna(0)

            def label_fn(x: float) -> str:
                if x > 0.2:
                    return "booming"
                if x < -0.1:
                    return "declining"
                return "stable"

            g["trend_label"] = g["future_growth_pct"].apply(lambda x: label_fn(float(x) if pd.notnull(x) else 0.0))
            rows.append(g)

        if not rows:
            return pd.DataFrame()
        dataset = pd.concat(rows, ignore_index=True)
        return dataset

    def train(self, horizon_days: int = 7, run_id: str | None = None):
        df = self.build_dataset(horizon_days=horizon_days)
        if df.empty:
            logger.info("No dataset available to train")
            return None

        # select numeric features (exclude known non-feature cols)
        exclude = {"tech", "date", "timestamp", "future_score", "future_growth_pct", "trend_label"}
        # use pandas' is_numeric_dtype to handle pandas extension dtypes safely
        feature_cols = [c for c in df.columns if c not in exclude and is_numeric_dtype(df[c])]
        if not feature_cols:
            logger.info("No numeric feature columns found")
            return None

        df_sorted = df.sort_values(["date", "tech"]).reset_index(drop=True)
        X = df_sorted[feature_cols].fillna(0)
        y = df_sorted["trend_label"]
        y_growth = pd.to_numeric(df_sorted["future_growth_pct"], errors="coerce").replace([np.inf, -np.inf], 0).fillna(0)

        # time-series cross-validation (expanding window)
        results = {}
        cv_results = {}
        def _time_series_cv_estimate(model_cls, name, n_splits=3):
            accs = []
            folds = []
            n = len(df)
            if n < 10:
                return {"accuracy": None}
            for i in range(1, n_splits + 1):
                train_end = int(n * (0.5 + 0.15 * i))
                test_end = min(n, train_end + int(n * 0.1))
                if train_end >= test_end:
                    continue
                X_tr = X.iloc[:train_end]
                y_tr = y.iloc[:train_end]
                X_te = X.iloc[train_end:test_end]
                y_te = y.iloc[train_end:test_end]
                try:
                    m = model_cls
                    m.fit(X_tr, y_tr)
                    preds = m.predict(X_te)
                    report = classification_report(y_te, preds, output_dict=True, zero_division=0)
                    acc = report.get("accuracy", 0)
                    accs.append(acc)
                    folds.append({"train_end": train_end, "test_end": test_end, "accuracy": acc, "report": report})
                except Exception:
                    logger.exception("CV fold failed for %s", name)
            if accs:
                return {"accuracy": float(np.mean(accs)), "folds": folds}
            return {"accuracy": None, "folds": folds}

        rf_estimators = getattr(settings, "ML_RANDOM_FOREST_ESTIMATORS", 100)

        # baseline: RandomForest
        rf = RandomForestClassifier(n_estimators=rf_estimators, random_state=42, n_jobs=-1)
        rf_cv = _time_series_cv_estimate(RandomForestClassifier(n_estimators=rf_estimators, random_state=42, n_jobs=-1), "random_forest")
        results["random_forest_cv"] = rf_cv

        # train final RF on the oldest 80% and evaluate on the newest 20%
        cutoff = int(len(df_sorted) * 0.8)
        cutoff = max(1, min(cutoff, len(df_sorted) - 1))
        X_train = X.iloc[:cutoff]
        X_test = X.iloc[cutoff:]
        y_train = y.iloc[:cutoff]
        y_test = y.iloc[cutoff:]
        y_growth_train = y_growth.iloc[:cutoff]
        y_growth_test = y_growth.iloc[cutoff:]

        rf.fit(X_train, y_train)
        preds_rf = rf.predict(X_test)
        report_rf = classification_report(y_test, preds_rf, output_dict=True, zero_division=0)
        cm_rf = confusion_matrix(y_test, preds_rf).tolist()
        results["random_forest_holdout"] = {"report": report_rf, "confusion_matrix": cm_rf}

        best_model = rf
        best_score = report_rf.get("accuracy", 0)

        # XGBoost (optional)
        if xgb is not None and getattr(settings, "ML_TRAIN_XGBOOST", False):
            try:
                xg = xgb.XGBClassifier(use_label_encoder=False, eval_metric="mlogloss")
                xg_cv = _time_series_cv_estimate(xgb.XGBClassifier(use_label_encoder=False, eval_metric="mlogloss"), "xgboost")
                results["xgboost_cv"] = xg_cv
                xg.fit(X_train, y_train)
                preds_xg = xg.predict(X_test)
                report_xg = classification_report(y_test, preds_xg, output_dict=True, zero_division=0)
                cm_xg = confusion_matrix(y_test, preds_xg).tolist()
                results["xgboost_holdout"] = {"report": report_xg, "confusion_matrix": cm_xg}
                if report_xg.get("accuracy", 0) > best_score:
                    best_model = xg
                    best_score = report_xg.get("accuracy", 0)
            except Exception:
                logger.exception("XGBoost training failed")

        # compute confidence on holdout set using predict_proba (if available)
        try:
            proba_vals = None
            if hasattr(best_model, "predict_proba"):
                proba = best_model.predict_proba(X_test)
                proba_vals = float(np.max(proba, axis=1).mean())
            else:
                proba_vals = None
        except Exception:
            logger.exception("Failed to compute predict_proba")
            proba_vals = None

        # Numeric growth regressor for /forecast predicted_growth.
        regression_model = None
        try:
            regression_model = RandomForestRegressor(
                n_estimators=rf_estimators,
                random_state=42,
                n_jobs=-1,
                min_samples_leaf=2,
            )
            regression_model.fit(X_train, y_growth_train)
            growth_preds = regression_model.predict(X_test)
            regression_report = {
                "mae": float(mean_absolute_error(y_growth_test, growth_preds)),
                "r2": float(r2_score(y_growth_test, growth_preds)) if len(y_growth_test) > 1 else None,
                "target_mean": float(y_growth.mean()),
            }
            results["random_forest_regressor_holdout"] = regression_report
        except Exception:
            logger.exception("Regression training failed")
            regression_model = None

        # save model artifact
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        # feature importances
        importances = None
        try:
            if hasattr(best_model, "feature_importances_"):
                importances = dict(zip(feature_cols, best_model.feature_importances_.tolist()))
            elif xgb is not None and isinstance(best_model, xgb.XGBClassifier):
                importances = dict(zip(feature_cols, best_model.feature_importances_.tolist()))
        except Exception:
            logger.exception("Failed to extract feature importances")

        model_artifact = {
            "model": best_model,
            "regression_model": regression_model,
            "feature_columns": feature_cols,
            "trained_at": timestamp,
            "horizon_days": horizon_days,
            "holdout_confidence": proba_vals,
            "feature_importances": importances,
        }
        model_path = self.model_dir / f"model_{timestamp}.joblib"
        joblib.dump(model_artifact, model_path)

        # save metrics/artifacts
        metrics: dict[str, Any] = {
            "training_timestamp": timestamp,
            "model_used": type(best_model).__name__,
            "target_variable": "trend_label",
            "horizon_days": horizon_days,
            "training_rows": int(len(X_train)),
            "testing_rows": int(len(X_test)),
            "training_shape": [int(X_train.shape[0]), int(X_train.shape[1])],
            "testing_shape": [int(X_test.shape[0]), int(X_test.shape[1])],
            "feature_columns": feature_cols,
            "feature_count": int(len(feature_cols)),
            "results": results,
            "holdout_confidence": proba_vals,
            "model_path": str(model_path),
        }
        metrics_path = self.artifacts_dir / f"metrics_{timestamp}.json"
        try:
            metrics_path.write_text(json.dumps(metrics, indent=2))
        except Exception:
            logger.exception("Failed to write metrics to %s", metrics_path)

        # save feature importances file
        try:
            if importances is not None:
                fi_path = self.artifacts_dir / f"feature_importances_{timestamp}.json"
                fi_path.write_text(json.dumps(importances, indent=2))
                metrics["feature_importances_path"] = str(fi_path)
        except Exception:
            logger.exception("Failed to persist feature importances")

        logger.info("Training complete. Best model saved to %s", model_path)

        # optional: train prophet per-tech for forecasting popularity
        if Prophet is not None and getattr(settings, "ML_TRAIN_PROPHET", False):
            try:
                prophet_dir = self.model_dir / "prophet"
                prophet_dir.mkdir(parents=True, exist_ok=True)
                for tech, g in df.groupby("tech"):
                    ts = g[["date", "technology_popularity_score"]].dropna()
                    if len(ts) < 10:
                        continue
                    ts = ts.rename(columns={"date": "ds", "technology_popularity_score": "y"})
                    ts["ds"] = pd.to_datetime(ts["ds"]) 
                    m = Prophet()
                    m.fit(ts)
                    joblib.dump(m, prophet_dir / f"prophet_{tech}_{timestamp}.joblib")
            except Exception:
                logger.exception("Prophet training failed or is not available")

        metrics["metrics_path"] = str(metrics_path)
        metrics["feature_importances"] = importances
        try:
            metrics_path.write_text(json.dumps(metrics, indent=2))
        except Exception:
            logger.exception("Failed to refresh metrics at %s", metrics_path)
        if db_repo is not None:
            db_model_id = db_repo.create_ml_model_record(metrics, external_run_id=run_id)
            if db_model_id:
                metrics["db_model_id"] = db_model_id
        return metrics


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--horizon", type=int, default=7)
    args = parser.parse_args()
    if args.train:
        ModelTrainer().train(horizon_days=args.horizon)
