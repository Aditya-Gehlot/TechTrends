#!/usr/bin/env python3
import sys
from pathlib import Path
import joblib
import pandas as pd
import numpy as np

# ensure project root on path
sys.path.insert(0, r'D:/Tech trends/project-root')
from config import settings


def main():
    tech = "AI Agents"
    model_dir = Path(settings.ML_MODELS_DIR)
    models = sorted(model_dir.glob("*.joblib"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not models:
        print("No models found")
        return
    artifact = joblib.load(models[0])
    model = artifact.get("model")
    feature_columns = artifact.get("feature_columns")

    feature_path = Path(settings.FEATURE_STORE_DIR) / "features_all.parquet"
    if not feature_path.exists():
        print("No consolidated feature file found")
        return
    df = pd.read_parquet(feature_path)
    df = df[df["tech"].astype(str).str.casefold() == tech.casefold()]
    if df.empty:
        print("No feature rows for tech", tech)
        return
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    row = df.sort_values("timestamp").tail(1).iloc[0].to_dict()
    features = {k: v for k, v in row.items() if k not in ("date", "timestamp", "tech")}

    if feature_columns:
        vals = [float(features.get(c, 0.0) or 0.0) for c in feature_columns]
        X_arr = pd.DataFrame([vals], columns=feature_columns)
    else:
        vals = [float(v) for k, v in features.items() if isinstance(v, (int, float))]
        if not vals:
            print("No numeric features found")
            return
        X_arr = np.array(vals).reshape(1, -1)

    pred = model.predict(X_arr)
    growth = None
    reg = artifact.get("regression_model")
    if reg is not None:
        growth = float(reg.predict(X_arr)[0])
    proba = None
    if hasattr(model, "predict_proba"):
        try:
            proba = float(model.predict_proba(X_arr).max())
        except Exception:
            proba = None

    print("Tech:", tech)
    print("Pred:", pred)
    print("Predicted growth:", growth)
    print("Proba:", proba)
    print("Feature columns:", feature_columns)


if __name__ == "__main__":
    main()
