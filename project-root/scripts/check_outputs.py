"""Quick verification of pipeline outputs.

Prints counts and example paths for processed parquet files, feature store files,
and trained model artifacts so you can validate the offline pipeline results.
"""
from pathlib import Path
from config import settings


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
    base = Path(settings.BASE_DIR)
    processed = Path(settings.PROCESSED_DIR)
    features = Path(settings.FEATURE_STORE_DIR) / "features"
    models = Path(settings.ML_MODELS_DIR)

    print("Processed parquet files:", count_files(processed, "*.parquet"))
    print("Example processed file:", sample_file(processed, "*.parquet"))
    print("Feature files:", count_files(features, "*.parquet"))
    print("Example feature file:", sample_file(features, "*.parquet"))
    print("Model artifacts:", count_files(models, "*.joblib"))
    print("Example model:", sample_file(models, "*.joblib"))


if __name__ == "__main__":
    main()
