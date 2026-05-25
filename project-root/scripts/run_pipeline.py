"""Orchestration script to run processing -> features -> training.

Usage: python scripts/run_pipeline.py
"""
import logging
from pathlib import Path
from config import settings
from processing.processor import S3Processor
from processing.local_processor import LocalProcessor
from feature_store.engineer import FeatureEngineer
from ml.train import ModelTrainer

logging.basicConfig(level=settings.LOG_LEVEL)


def main():
    data_dir = Path(settings.BASE_DIR) / "Data"
    if data_dir.exists():
        logging.info("Data folder found — running Local CSV processing")
        proc = LocalProcessor(data_dir)
        proc.run_all()
    else:
        proc = S3Processor()
        logging.info("Running S3 processing (run-once)")
        proc.run(run_once=True)

    fe = FeatureEngineer()
    logging.info("Generating features")
    fe.generate_daily_features()

    mt = ModelTrainer()
    logging.info("Training models")
    mt.train()


if __name__ == "__main__":
    main()
