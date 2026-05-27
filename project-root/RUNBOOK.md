# TechTrends Runbook

This project has two runnable modes:

1. Local offline pipeline using the generated sample corpus in `Data/`
2. Streaming pipeline using Kafka plus S3/MinIO

The local offline path is the fastest way to validate the ML pipeline on this checkout.

## Requirements

- Windows PowerShell, macOS shell, or Linux shell
- Python 3.10 to 3.12 recommended
- `pip`
- Docker Desktop with `docker compose` for Kafka/MinIO runs

Notes:
- The current machine is using Python `3.13.3`. The repo may still work there, but `xgboost`, `prophet`, and other binary packages are more reliable on Python `3.10` to `3.12`.
- Run Python commands from `project-root/`.
- Use module-style commands such as `python -m scripts.run_pipeline`. Running `python scripts\run_pipeline.py` fails because of package imports.

## 1. Local Offline Pipeline

Use this when you want the pipeline to run entirely from the generated CSV files already present in `Data/`.

### Regenerate the large synthetic market-intelligence dataset

Run this when you want to rebuild the 2025-2026 synthetic corpus before the pipeline:

```powershell
python -m scripts.generate_market_intel_dataset
```

This updates the project-compatible CSVs in `Data/` and creates additional market-intelligence assets in `Data/market_intel/`, `imports/`, and `samples/`.

### Setup

```powershell
cd C:\TechTrends\project-root
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

`Data/` already exists in this repo, so `scripts.run_pipeline` will automatically use `processing.local_processor.LocalProcessor`.
The local processor now reads the top-level generated CSVs plus the event datasets under `Data/market_intel/`. `companies.csv` is written as a local dimension and is not counted as a trend event.

### Run the full local pipeline

```powershell
python -m scripts.run_pipeline --clean
```

This runs:

- CSV ingestion from `Data/` and `Data/market_intel/`
- Parquet generation into `processed/`
- Feature generation into `feature_store/features_all.parquet` and latest per-tech files in `feature_store/features/`
- Model training into `ml/models/` and `ml/artifacts/`

By default the feature layer writes one consolidated feature parquet plus one `latest.parquet` per technology. To also write one feature file per technology per date, add:

```powershell
python -m scripts.run_pipeline --clean --write-daily-partitions
```

For local runs, RandomForest is the default model. XGBoost and Prophet are disabled by default because they can make the expanded synthetic corpus slow to train. Enable them in `.env` only when needed:

```env
ML_TRAIN_XGBOOST=true
ML_TRAIN_PROPHET=true
```

### Start the API

```powershell
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

### Start the dashboard

In a second terminal:

```powershell
cd C:\TechTrends\project-root
.venv\Scripts\Activate.ps1
streamlit run dashboard\streamlit_app.py
```

The dashboard opens the `TechTrends Control Center`. Use the `Pipeline Control`
tab to start a full run from the UI. The button calls FastAPI and tracks the
same local pipeline stages that `python -m scripts.run_pipeline --clean` runs.

If your API is on a non-default port, set:

```powershell
$env:API_URL="http://127.0.0.1:8001"
streamlit run dashboard\streamlit_app.py
```

### Pipeline API checks

```powershell
Invoke-WebRequest http://localhost:8000/pipeline/status
Invoke-WebRequest http://localhost:8000/pipeline/metrics
Invoke-WebRequest http://localhost:8000/pipeline/runs
Invoke-WebRequest http://localhost:8000/pipeline/predictions/latest
```

### PostgreSQL persistence

Raw generated data remains file-based only. The DB layer starts at normalized
processed parquet and stores pipeline metadata, stage progress, feature rows,
feature snapshot metadata, model metadata, source summaries, and predictions.

Start PostgreSQL and apply migrations:

```powershell
docker-compose up -d db
alembic upgrade head
```

Run with DB persistence:

```powershell
$env:ENABLE_DB_PERSISTENCE="true"
$env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/techtrends"
python -m pipeline.runner
```

Backfill existing derived artifacts:

```powershell
$env:ENABLE_DB_PERSISTENCE="true"
python -m scripts.backfill_db_from_existing_artifacts
python -m scripts.backfill_db_from_existing_artifacts --store-normalized-records
```

Migration helpers:

```powershell
alembic revision --autogenerate -m "create techtrends database schema"
alembic upgrade head
alembic downgrade -1
```

### Quick checks

```powershell
Invoke-WebRequest http://localhost:8000/health
Invoke-WebRequest "http://localhost:8000/trends/top?limit=10"
```

## 2. Streaming Pipeline With Kafka + MinIO

Use this when you want producers to publish to Kafka and raw events to land in object storage before processing.

### Setup

```powershell
cd C:\TechTrends\project-root
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` for MinIO/local object storage:

```env
BOOTSTRAP_SERVERS=localhost:9092
RAW_S3_BUCKET=techtrends-raw
RAW_S3_REGION=us-east-1
RAW_S3_PREFIX=raw
RAW_S3_ENDPOINT_URL=http://localhost:9000
RAW_S3_ACCESS_KEY_ID=minioadmin
RAW_S3_SECRET_ACCESS_KEY=minioadmin
```

### Start infrastructure

```powershell
docker compose up -d
```

This starts:

- Zookeeper
- Kafka
- MinIO
- API container
- Kafka topic bootstrap container

### Run producers

```powershell
python main.py --all
```

Or individual producers:

```powershell
python main.py --google
python main.py --stackoverflow
python main.py --github
python main.py --blogs
```

### Persist Kafka raw data to object storage

In another terminal:

```powershell
cd C:\TechTrends\project-root
.venv\Scripts\Activate.ps1
python main.py --s3-raw-consumer
```

### Process raw objects from MinIO/S3

```powershell
python -m processing.processor --run-once
```

### Generate features and train models

```powershell
python -m feature_store.engineer
python -m ml.train --train
```

### Optional demo data path without Kafka producers

If you only want S3/MinIO sample raw files:

```powershell
python -m scripts.generate_demo_data
python -m processing.processor --run-once
python -m feature_store.engineer
python -m ml.train --train
```

## Useful Commands

### Kafka smoke test

```powershell
python smoke_test.py
```

### Full smoke demo

```powershell
python -m scripts.smoke_demo
```

### Show generated outputs

```powershell
Get-ChildItem processed -Recurse
Get-ChildItem feature_store\features -Recurse
Get-ChildItem ml\models -Recurse
Get-ChildItem ml\artifacts -Recurse
```

## Outputs

Expected directories after a successful local pipeline run:

- `processed/`
- `feature_store/features/`
- `ml/models/`
- `ml/artifacts/`

## Known Constraints

- `python scripts\run_pipeline.py` is not the correct command for this repo. Use `python -m scripts.run_pipeline`.
- The installed dependencies are required before running any module. Without them, imports such as `pydantic` and `joblib` will fail.
- If `prophet` fails to install on Windows, the main classification pipeline can still run, but Prophet-based forecasting models will be skipped.
- If you keep real AWS credentials in `.env`, do not commit that file.
