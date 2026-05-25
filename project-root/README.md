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
- `api/` : FastAPI app exposing `/trends/top`, `/technology/{name}`, `/forecast/{name}`, `/health`.
- `dashboard/` : Streamlit starter dashboard.

Quick run (local, minimal):

1. Start Kafka + MinIO using docker-compose

```bash
docker-compose up -d
```

2. Install Python deps (recommended venv)

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Configure `.env` (see `.env.example`) and export credentials for MinIO/AWS if needed.

4. Run processors (example: process raw S3 objects once)

```bash
python -m processing.processor --run-once
```

5. Generate features

```bash
python -m feature_store.engineer
```

6. Train a model (saves models to `ml/models`)

```bash
python -m ml.train --train
```

7. Run the API (locally)

```bash
uvicorn api.app:app --reload
```

8. Run the dashboard (locally)

```bash
streamlit run dashboard/streamlit_app.py
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
python scripts/run_pipeline.py
```
- Full smoke demo (generate, run pipeline, attempt API call):
```bash
python scripts/smoke_demo.py
```

