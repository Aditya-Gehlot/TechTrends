# Tech Trend Analytics — Real-Time Starter

This repository provides a minimal, production-minded starter for real-time tech trend ingestion using Python, Kafka and Docker.

Quick features
- Docker Compose to run Kafka + Zookeeper
- 4 producers: Google Trends, StackOverflow, GitHub events, Tech blog RSS
- Kafka utils (producer/consumer factories)
- Simple consumer to verify messages
- Raw ingestion consumer that writes newline-delimited JSON to S3/MinIO

Prerequisites
- Python 3.10+
- Docker & Docker Compose

Setup
1. Start Kafka locally (one command):

```bash
# from project root
docker-compose up -d
```

2. Install Python dependencies (recommended virtualenv)

```bash
python -m venv .venv
source .venv/bin/activate    # Linux / macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

3. Create local environment file

```powershell
Copy-Item .env.example .env
```

Then edit `.env` with your AWS and S3 values. The app now loads `.env` automatically on startup.

4. Configure (optional)
- See `config/settings.py` for environment variables. Common ones:
  - `BOOTSTRAP_SERVERS` (default: localhost:9092)
  - `GITHUB_TOKEN` (optional, avoid rate limits)
  - `RAW_S3_BUCKET` (required for S3 raw ingestion)
  - `RAW_S3_PREFIX` (default: `raw`)
  - `RAW_S3_REGION` (default: `us-east-1`)
  - `RAW_S3_ENDPOINT_URL` (use for MinIO or non-AWS S3)
  - `RAW_S3_ACCESS_KEY_ID` / `RAW_S3_SECRET_ACCESS_KEY`
  - `RAW_S3_BATCH_SIZE` (default: `100`)
  - `RAW_S3_FLUSH_INTERVAL` (default: `60` seconds)

Running producers

- Run all producers together:

```bash
python main.py --all
```

- Run individual producers:

```bash
python main.py --google
python main.py --stackoverflow
python main.py --github
python main.py --blogs
```

Consuming messages (verify)

```bash
python main.py --consumer
# or use the consumer module directly
python consumers/base_consumer.py --topics google_trends
```

Raw data ingestion to S3

1. Export your object-store settings.

You can either place these in `.env` or export them in the shell.

AWS S3:

```bash
export RAW_S3_BUCKET=my-techtrends-raw
export RAW_S3_REGION=us-east-1
export RAW_S3_PREFIX=raw
```

Windows PowerShell:

```powershell
$env:RAW_S3_BUCKET="my-techtrends-raw"
$env:RAW_S3_REGION="us-east-1"
$env:RAW_S3_PREFIX="raw"
```

MinIO / local S3-compatible storage:

```powershell
$env:RAW_S3_BUCKET="techtrends-raw"
$env:RAW_S3_REGION="us-east-1"
$env:RAW_S3_PREFIX="raw"
$env:RAW_S3_ENDPOINT_URL="http://localhost:9000"
$env:RAW_S3_ACCESS_KEY_ID="minioadmin"
$env:RAW_S3_SECRET_ACCESS_KEY="minioadmin"
```

2. Start producers:

```bash
python main.py --all
```

3. Start the raw-ingestion consumer in another terminal:

```bash
python main.py --s3-raw-consumer
```

This writes `.jsonl` objects like:

```text
raw/github_events/2026/05/23/143015-1748001015123.jsonl
```

Each line contains Kafka metadata plus the original producer payload:

```json
{"topic":"github_events","partition":0,"offset":12,"timestamp":1748001014000,"ingested_at":"2026-05-23T14:30:15.123456+00:00","payload":{"id":"123","type":"PushEvent"}}
```

Smoke test

You can run a quick programmatic smoke test that creates a topic, sends a message, and consumes it:

```bash
python smoke_test.py
```

Notes
- The docker-compose file creates the required topics automatically.
- Producers persist simple state in `.state/` to reduce duplicates while running.
- This starter keeps things small and framework-free so it can be extended with Spark/ML later.

Next steps (suggested)
- Add schema validation (pydantic) before publishing messages
- Add retries and backoff for producers (tenacity)
- Partition S3 keys further by source/hour if downstream Athena queries are planned

========================
AI / ML — Next Phase
========================

This repository now includes a Phase-1 AI/ML augmentation that processes raw JSONL from S3/MinIO into analytics-ready Parquet, produces feature vectors, trains models, serves predictions via FastAPI, and provides a Streamlit demo dashboard.

New top-level modules
- `processing/` : read raw JSONL from S3, normalize, clean, deduplicate and write Parquet.
- `feature_store/` : feature engineering and feature store (per-technology Parquet features).
- `ml/` : training scripts and model persistence under `ml/models/`.
- `api/` : FastAPI app exposing `/trends/top`, `/trends/history/{name}`, `/features/{name}`, `/technology/{name}`, `/forecast/{name}`, `/sources/summary`, `/models/latest`, `/health`.
- `dashboard/` : Streamlit starter dashboard.

Quick run (local generated sample data):

1. Install Python deps (recommended venv)

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the local generated-data pipeline

```bash
python -m scripts.run_pipeline --clean
```

This reads the generated CSVs in `Data/` and `Data/market_intel/`, writes processed parquet, builds `feature_store/features_all.parquet`, trains classification and regression models, and saves artifacts under `ml/models/` and `ml/artifacts/`.

3. Run the API

```bash
uvicorn api.app:app --reload
```

4. Run the dashboard

```bash
streamlit run dashboard/streamlit_app.py
```

Pipeline Control Center

The Streamlit app now includes a UI control plane for the local pipeline:

- `Pipeline Control`: start a full run from a button, track stages, logs, and stage-level metrics.
- `Live Insights`: records processed, inserted, rejected, duplicates, missing values, outliers, feature counts, prediction counts, and layer dimensions.
- `Feature Layer`: created features, selected features, dropped features with reasons, transformation categories, null percentages, dtypes, and correlations.
- `ML & Predictions`: model metadata, train/test sizes, accuracy, MAE/R2, feature importance, and latest predictions.
- `Run History`: previous runs with run ID, trigger, status, duration, records, features, model score, and error details.

The UI calls FastAPI endpoints; the command-line pipeline remains available.

Pipeline API endpoints:

- `POST /pipeline/run`
- `GET /pipeline/status`
- `GET /pipeline/metrics`
- `GET /pipeline/runs`
- `GET /pipeline/runs/{run_id}`
- `GET /pipeline/runs/{run_id}/logs`
- `GET /pipeline/predictions/latest`

PostgreSQL Persistence
----------------------

The project can optionally persist derived pipeline data to PostgreSQL. Raw
generated files stay local only: `Data/*.csv`, `Data/market_intel/*.csv`, raw
parquet directories, and `imports/` are not imported as raw database tables.

Database persistence starts at normalized/processed data and derived metadata:

- `pipeline_runs` and `pipeline_stages`
- `normalized_records` from `processed/**/*.parquet` when `STORE_NORMALIZED_RECORDS=true`
- `daily_features` from `feature_store/features_all.parquet`
- `feature_snapshots`
- `ml_models` metadata and artifact paths
- `predictions`
- `data_sources_summary`

Setup:

```bash
pip install -r requirements.txt
docker-compose up -d db
alembic upgrade head
```

Useful migration commands:

```bash
alembic revision --autogenerate -m "create techtrends database schema"
alembic upgrade head
alembic downgrade -1
```

Run with DB persistence:

```bash
ENABLE_DB_PERSISTENCE=true python -m pipeline.runner
```

Backfill from existing derived artifacts:

```bash
ENABLE_DB_PERSISTENCE=true python -m scripts.backfill_db_from_existing_artifacts
ENABLE_DB_PERSISTENCE=true python -m scripts.backfill_db_from_existing_artifacts --store-normalized-records
```

FastAPI reads PostgreSQL first for pipeline runs, stages, predictions, trend
history, latest features, model metadata, and source summaries. If the DB is
disabled, unreachable, or empty, it falls back to the existing local files.

Streaming/Kafka/MinIO remains available when you want the raw-object path:

```bash
docker-compose up -d
python -m processing.processor --run-once
```


Notes
- The new processing/feature/ML layers are intentionally small, readable, and designed to be extended for production: add distributed compute (Dask/Spark), scheduling (Airflow), and model registry (MLflow) as next steps.
- See `.env.example` for environment variables used by the new modules.

Quick demo scripts

- Generate demo raw data to S3/MinIO:
```bash
python scripts/generate_demo_data.py
```
- Run the pipeline (process -> features -> train):
```bash
python -m scripts.run_pipeline --clean
```
- Full smoke demo (generate, run pipeline, attempt API call):
```bash
python -m scripts.smoke_demo
```

