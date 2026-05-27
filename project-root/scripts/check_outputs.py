"""Quick verification of pipeline outputs.

Prints counts and example paths for processed parquet files, feature store files,
and trained model artifacts so you can validate the offline pipeline results.
"""
from pathlib import Path
from config import settings
import joblib
import pandas as pd


def count_files(path: Path, ext: str = "*.parquet"):
    if not path.exists():
        return 0
    return sum(1 for _ in path.rglob(ext))


def sample_file(path: Path, ext: str = "*.parquet"):
    if not path.exists():
        return None
    files = list(path.rglob(ext))
    return str(files[0]) if files else None


def main():
    processed = Path(settings.PROCESSED_DIR)
    features = Path(settings.FEATURE_STORE_DIR) / "features"
    features_all = Path(settings.FEATURE_STORE_DIR) / "features_all.parquet"
    models = Path(settings.ML_MODELS_DIR)

    print("Processed parquet files:", count_files(processed, "*.parquet"))
    print("Example processed file:", sample_file(processed, "*.parquet"))
    print("Feature files:", count_files(features, "*.parquet"))
    print("Example feature file:", sample_file(features, "*.parquet"))
    if features_all.exists():
        df = pd.read_parquet(features_all)
        print("Consolidated feature rows:", len(df))
        print("Consolidated technologies:", df["tech"].nunique() if "tech" in df.columns else 0)
        if "date" in df.columns:
            print("Feature date range:", f"{pd.to_datetime(df['date']).min().date()} to {pd.to_datetime(df['date']).max().date()}")
    print("Model artifacts:", count_files(models, "*.joblib"))
    latest = None
    if models.exists():
        model_files = sorted(models.glob("*.joblib"), key=lambda p: p.stat().st_mtime, reverse=True)
        latest = model_files[0] if model_files else None
    print("Latest model:", latest)
    if latest:
        artifact = joblib.load(latest)
        if isinstance(artifact, dict):
            print("Latest model trained_at:", artifact.get("trained_at"))
            print("Feature columns:", len(artifact.get("feature_columns") or []))
            print("Has regression model:", artifact.get("regression_model") is not None)


if __name__ == "__main__":
    main()
