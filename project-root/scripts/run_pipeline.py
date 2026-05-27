"""Run the local processing -> features -> training pipeline.

Use the generated sample data by default:

    python -m scripts.run_pipeline
"""
from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path

from config import settings
from feature_store.engineer import FeatureEngineer
from ml.train import ModelTrainer
from processing.local_processor import LocalProcessor

logging.basicConfig(level=settings.LOG_LEVEL, format="%(levelname)s:%(name)s:%(message)s")


def _clean_local_outputs() -> None:
    """Remove local derived artifacts so a run is based only on current sample data."""
    targets = [
        Path(settings.PROCESSED_DIR),
        Path(settings.FEATURE_STORE_DIR) / "features",
        Path(settings.FEATURE_STORE_DIR) / "features_all.parquet",
        Path(settings.FEATURE_STORE_DIR) / "feature_index.json",
    ]
    for target in targets:
        if target.is_dir():
            shutil.rmtree(target)
            logging.info("Removed derived directory %s", target)
        elif target.exists():
            target.unlink()
            logging.info("Removed derived file %s", target)
    Path(settings.PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.FEATURE_STORE_DIR).mkdir(parents=True, exist_ok=True)


def _local_pipeline(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir) if args.data_dir else Path(settings.BASE_DIR) / "Data"
    processor = LocalProcessor(data_dir)
    results = processor.run_all()
    sources = [source for source in processor.EVENT_SOURCES if results.get(source, 0) > 0]

    logging.info("Generating features from local sources: %s", ", ".join(sources))
    feature_engineer = FeatureEngineer()
    feature_engineer.generate_daily_features(
        sources=sources,
        write_partitions=args.write_daily_partitions,
    )

    if not args.skip_training:
        logging.info("Training models")
        ModelTrainer().train(horizon_days=args.horizon)


def _s3_pipeline(args: argparse.Namespace) -> None:
    from processing.processor import S3Processor

    processor = S3Processor()
    logging.info("Running S3 processing once")
    processor.run(run_once=True)

    feature_engineer = FeatureEngineer()
    feature_engineer.generate_daily_features(write_partitions=args.write_daily_partitions)

    if not args.skip_training:
        ModelTrainer().train(horizon_days=args.horizon)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=None, help="Local generated CSV data directory. Defaults to Data/.")
    parser.add_argument("--horizon", type=int, default=7, help="Prediction horizon in days.")
    parser.add_argument("--skip-training", action="store_true", help="Run processing and features only.")
    parser.add_argument("--write-daily-partitions", action="store_true", help="Write one feature parquet per tech per date.")
    parser.add_argument("--clean", action="store_true", help="Remove local processed/features outputs before running.")
    parser.add_argument("--s3", action="store_true", help="Use S3/MinIO raw processing instead of local CSV data.")
    args = parser.parse_args()

    if args.clean:
        _clean_local_outputs()

    data_dir = Path(args.data_dir) if args.data_dir else Path(settings.BASE_DIR) / "Data"
    if not args.s3 and data_dir.exists():
        logging.info("Data folder found - running local generated-data processing")
        _local_pipeline(args)
    else:
        _s3_pipeline(args)


if __name__ == "__main__":
    main()
