# TechTrends Current Architecture Reference

This file is the single-source reference for the current TechTrends project as it exists in this repository today.

It explains:

- what the project does
- which runtime paths exist
- which path is active for the current local sample-data workflow
- every important folder and file
- how data moves from raw files to processed parquet to features to models to API/dashboard
- what is stored on disk vs in PostgreSQL
- which generated artifacts exist
- how the pieces depend on each other
- which commands and services are involved

This document describes the current implemented architecture, not only the aspirational one.

---

## 1. Project Purpose

TechTrends is a tech market intelligence pipeline that:

1. collects or generates technology market data
2. normalizes multi-source records into a shared schema
3. writes normalized daily parquet partitions
4. engineers daily per-technology features
5. trains ML models for trend classification and growth prediction
6. generates latest predictions
7. serves results through FastAPI
8. visualizes pipeline state, features, ML metrics, and predictions in Streamlit
9. optionally persists derived data and metadata to PostgreSQL

The project supports two modes:

1. local offline mode using generated sample data in `Data/`
2. streaming mode using Kafka plus S3/MinIO

For the current working setup, the primary active path is the local offline mode.

---

## 2. High-Level Flow

### 2.1 Current local path

```text
scripts/generate_market_intel_dataset.py
    -> Data/*.csv + Data/market_intel/*.csv
    -> processing/local_processor.py
    -> processed/<source>/<yyyy>/<mm>/<dd>/<date>.parquet
    -> feature_store/engineer.py
    -> feature_store/features_all.parquet
    -> feature_store/features/<tech>/latest.parquet
    -> ml/train.py
    -> ml/models/*.joblib + ml/artifacts/*.json
    -> pipeline/runner.py prediction generation
    -> feature_store/predictions_latest.parquet/json
    -> api/app.py
    -> dashboard/streamlit_app.py
```

### 2.2 Optional PostgreSQL persistence path

```text
processed parquet
    -> db.normalized_records
    -> db.data_sources_summary

feature_store/features_all.parquet
    -> db.daily_features
    -> db.feature_snapshots

ml/models/*.joblib + ml/artifacts/*.json
    -> db.ml_models

feature_store/predictions_latest.*
    -> db.predictions

pipeline state during run
    -> db.pipeline_runs
    -> db.pipeline_stages
```

### 2.3 Optional streaming path

```text
producers/*.py
    -> Kafka topics
    -> consumers/s3_raw_consumer.py
    -> S3/MinIO raw JSONL
    -> processing/processor.py
    -> processed parquet
    -> same feature / ML / API / dashboard flow as local mode
```

---

## 3. Top-Level Repository Structure

```text
project-root/
  .state/                    File-based pipeline state and run history
  alembic/                   DB migration environment and versions
  api/                       FastAPI application
  config/                    Environment and path settings
  consumers/                 Kafka consumers
  dashboard/                 Streamlit UI
  Data/                      Local generated sample datasets and raw generated parquet variants
  db/                        SQLAlchemy models, sessions, repositories
  docker/                    Optional docker-related assets
  feature_store/             Engineered feature artifacts and latest predictions
  imports/                   Generated NDJSON / Elasticsearch / SQL import helper files
  logs/                      Local logs
  ml/                        Model training code and artifacts
  pipeline/                  UI/API-oriented pipeline runner
  processed/                 Normalized parquet partitions
  processing/                Local CSV processor and S3 raw processor
  producers/                 Streaming source producers
  samples/                   Generated API and JSON examples
  scripts/                   CLI and utility scripts
  utils/                     Shared Kafka/S3 helpers
  docker-compose.yml         Local infrastructure services
  Dockerfile.api             API container image
  main.py                    Producer/consumer runner entrypoint
  README.md                  Main setup and overview
  RUNBOOK.md                 Operational runbook
  PROJECT_FLOW.md            Shorter flow document
  CURRENT_ARCHITECTURE.md    This file
```

---

## 4. Runtime Modes

## 4.1 Local offline mode

This is the main current path.

Input:

- `Data/*.csv`
- `Data/market_intel/*.csv`

Core modules:

- `scripts/generate_market_intel_dataset.py`
- `processing/local_processor.py`
- `feature_store/engineer.py`
- `ml/train.py`
- `pipeline/runner.py`
- `api/app.py`
- `dashboard/streamlit_app.py`

Outputs:

- `processed/`
- `feature_store/`
- `ml/models/`
- `ml/artifacts/`
- `.state/`
- optional PostgreSQL rows

## 4.2 Streaming mode

This exists in the repo, but is secondary for the current sample-data workflow.

Input:

- Google Trends
- StackOverflow
- GitHub Events
- RSS/blog feeds

Core modules:

- `producers/google_trends_producer.py`
- `producers/stackoverflow_producer.py`
- `producers/github_producer.py`
- `producers/blog_producer.py`
- `consumers/s3_raw_consumer.py`
- `processing/processor.py`

Infrastructure:

- Kafka
- Zookeeper
- MinIO / S3-compatible storage

---

## 5. Configuration and Environment

Primary config file:

- `config/settings.py`

Environment file:

- `.env`

Example environment:

- `.env.example`

Important settings currently used:

### General

- `BASE_DIR`
- `STATE_DIR`
- `LOG_LEVEL`

### Local derived paths

- `PROCESSED_DIR`
- `FEATURE_STORE_DIR`
- `ML_MODELS_DIR`

### Feature and ML

- `FEATURE_WINDOW_DAYS`
- `FEATURE_WRITE_DAILY_PARTITIONS`
- `ML_TRAIN_XGBOOST`
- `ML_TRAIN_PROPHET`
- `ML_RANDOM_FOREST_ESTIMATORS`

### PostgreSQL

- `DATABASE_URL`
- `ENABLE_DB_PERSISTENCE`
- `STORE_NORMALIZED_RECORDS`
- `CLEAN_DB_LATEST_ONLY`
- `DB_BATCH_SIZE`
- `DB_ECHO`

### Streaming / Kafka / object storage

- `BOOTSTRAP_SERVERS`
- `RAW_S3_BUCKET`
- `RAW_S3_PREFIX`
- `RAW_S3_REGION`
- `RAW_S3_ENDPOINT_URL`
- `RAW_S3_ACCESS_KEY_ID`
- `RAW_S3_SECRET_ACCESS_KEY`

Current local DB default:

```text
postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/techtrends
```

---

## 6. External Dependencies

From `requirements.txt`:

### Data / ingestion

- `kafka-python`
- `pytrends`
- `requests`
- `feedparser`
- `boto3`

### Data processing

- `pandas`
- `numpy`
- `pyarrow`
- `pydantic`

### API / UI

- `fastapi`
- `uvicorn[standard]`
- `streamlit`
- `plotly`

### ML

- `scikit-learn`
- `xgboost`
- `prophet`
- `joblib`
- `mlflow`

### Database

- `sqlalchemy`
- `alembic`
- `psycopg2-binary`
- `python-dotenv`

---

## 7. Local Infrastructure Services

Defined in `docker-compose.yml`:

### `db`

- image: `postgres:16`
- host port: `5433`
- container port: `5432`
- db: `techtrends`
- user: `postgres`
- password: `postgres`

### `zookeeper`

- port: `2181`

### `kafka`

- host ports: `9092`, `29092`

### `minio`

- port: `9000`

### `api`

- Dockerized FastAPI container
- port: `8000`
- inside compose it uses DB host `db:5432`

### `kafka-setup`

- topic bootstrap helper

Important note:

- Your Streamlit UI may point to `127.0.0.1:8001` or `127.0.0.1:8000`
- `dashboard/streamlit_app.py` includes a fallback that switches between `8001` and `8000`

---

## 8. Raw Input Layer

## 8.1 Local generated datasets

Main generated files:

- `Data/linkedin_jobs.csv`
- `Data/twitter_stream.csv`
- `Data/github_events.csv`
- `Data/tech_blogs.csv`
- `Data/stackoverflow_questions.csv`
- `Data/google_trends.csv`
- `Data/market_intel/reddit_discussions.csv`
- `Data/market_intel/hackernews_posts.csv`
- `Data/market_intel/youtube_ai_content.csv`
- `Data/market_intel/startup_funding.csv`
- `Data/market_intel/producthunt_launches.csv`
- `Data/market_intel/news_media_mentions.csv`
- `Data/market_intel/kaggle_ml_activity.csv`
- `Data/market_intel/market_events.csv`
- `Data/market_intel/companies.csv`

Additional generated raw helper artifacts:

- `Data/**/*.csv.gz`
- `Data/**/*.parquet`
- partitioned raw parquet folders under `Data/<dataset>/year=*/month=*`
- `Data/dataset_summary.json`
- `Data/market_intel/dataset_summary.json`
- `Data/market_intel/market_context_2026.json`
- `Data/market_intel/schemas/*.schema.json`

Important implementation note:

- the active local processing pipeline reads the CSV files
- the generated parquet variants under `Data/` are auxiliary export artifacts, not the main local input for `LocalProcessor`

## 8.2 Generated import/export helper files

Written by `scripts/generate_market_intel_dataset.py`:

- `imports/*.ndjson`
- `imports/*.es.bulk.ndjson`
- `imports/seed_load.sql`
- `imports/validation_report.json`

These are helper outputs only. They are not the main source for the pipeline runtime.

## 8.3 File ownership boundary

Raw generated files remain file-based only.

They are not stored as raw tables in PostgreSQL.

The DB boundary begins after normalization / processing.

---

## 9. Data Generation Layer

Main script:

- `scripts/generate_market_intel_dataset.py`

Purpose:

- create realistic synthetic sample data aligned with a 2025-2026 market narrative
- output multiple formats for local processing and optional import/export use

Important outputs:

- core CSVs in `Data/`
- market-intel CSVs in `Data/market_intel/`
- raw parquet export variants in `Data/`
- `imports/` helper files
- `samples/` example payloads
- JSON schemas in `Data/market_intel/schemas/`

Related docs:

- `DATA_GENERATION_RUNBOOK.md`

---

## 10. Processing Layer

## 10.1 Local CSV processor

Main file:

- `processing/local_processor.py`

Purpose:

- read generated CSV datasets
- normalize each source into a common event schema
- write daily parquet partitions to `processed/`
- optionally persist normalized records and source summaries to PostgreSQL

Related schema:

- `processing/schemas.py`

Key Pydantic models:

### `RawRecord`

Used by streaming/raw pipeline:

- `topic`
- `partition`
- `offset`
- `timestamp`
- `ingested_at`
- `payload`

### `NormalizedRecord`

Shared normalized event shape:

- `source`
- `id`
- `timestamp`
- `title`
- `text`
- `tags`
- `url`
- `techs`
- `raw`

## 10.2 Supported local event sources in `LocalProcessor`

- `linkedin_jobs`
- `twitter_stream`
- `github_events`
- `tech_blogs`
- `stackoverflow_questions`
- `google_trends`
- `reddit_discussions`
- `hackernews_posts`
- `youtube_ai_content`
- `startup_funding`
- `producthunt_launches`
- `news_media_mentions`
- `kaggle_ml_activity`
- `market_events`

Dimension handled separately:

- `companies_dimension`

## 10.3 Processed output format

Local normalized parquet is written as:

```text
processed/<source>/<yyyy>/<mm>/<dd>/<date>.parquet
```

Examples:

- `processed/linkedin_jobs/2026/01/01/2026-01-01.parquet`
- `processed/twitter_stream/2025/06/14/2025-06-14.parquet`

Dimension output:

- `processed/_dimensions/companies.parquet`

## 10.4 Streaming processor

Main file:

- `processing/processor.py`

Purpose:

- read raw JSONL from S3/MinIO
- normalize to the same general structure
- write processed parquet

This path exists but is not the primary one for the current UI-driven sample-data workflow.

---

## 11. Processed Layer on Disk

Directory:

- `processed/`

Contents:

- one folder per normalized source
- partitioned parquet files by date
- `_dimensions/companies.parquet`

Role:

- this is the source of truth for feature engineering
- optional DB backfill also starts here

Optional DB mirror:

- `normalized_records`
- `data_sources_summary`

---

## 12. Feature Engineering Layer

Main file:

- `feature_store/engineer.py`

Purpose:

- read normalized processed parquet
- aggregate daily metrics by technology
- build engineered rolling and lag-based features
- write consolidated and per-tech feature artifacts
- optionally persist feature rows and snapshot metadata to PostgreSQL

## 12.1 Feature engineering inputs

Input source:

- `processed/**/*.parquet`

Grouping logic:

- primarily by `tech` and `date`

## 12.2 Main on-disk feature artifacts

Directory:

- `feature_store/`

Files:

- `feature_store/features_all.parquet`
- `feature_store/feature_index.json`
- `feature_store/features/<tech>/latest.parquet`

Optional, only when enabled:

- daily per-tech feature partitions under `feature_store/features/<tech>/<date>.parquet`

Current default:

- one consolidated parquet
- one latest parquet per technology
- no daily feature partitions unless `FEATURE_WRITE_DAILY_PARTITIONS=true`

## 12.3 Important engineered feature families

Examples:

- source counts
- mention counts
- trend score averages
- sentiment averages
- innovation and adoption averages
- salary averages
- job posting counts
- GitHub activity counts and sums
- StackOverflow counts and engagement
- Google trend score averages
- community/blog/news/video engagement
- funding metrics
- market event impact metrics
- rolling 7-day and 30-day means and sums
- lag features
- velocity features
- growth percentages
- spike indicators
- composite scores:
  - `technology_popularity_score`
  - `ecosystem_momentum_score`

## 12.4 Optional DB persistence for features

Tables:

- `daily_features`
- `feature_snapshots`

`daily_features.features` stores the dynamic feature set in JSONB.

Promoted columns also stored separately:

- `tech`
- `date`
- `source`
- `technology_popularity_score`
- `ecosystem_momentum_score`

---

## 13. ML Training Layer

Main file:

- `ml/train.py`

Purpose:

- load feature data
- build the ML dataset
- create future labels
- train classifier and regressor
- save model and metrics artifacts
- optionally persist model metadata to PostgreSQL

## 13.1 ML dataset source

Primary source:

- `feature_store/features_all.parquet`

Fallback:

- `feature_store/features/**/*.parquet` if consolidated file is missing

## 13.2 Current modeling approach

Primary classification target:

- `trend_label`

Derived by future 7-day popularity behavior, using:

- `future_score`
- `future_growth_pct`

Classification states:

- `booming`
- `stable`
- `declining`

Models:

- `RandomForestClassifier`
- `RandomForestRegressor`

Optional:

- `XGBoost`
- `Prophet` per-technology forecasting

## 13.3 On-disk ML artifacts

Directories:

- `ml/models/`
- `ml/artifacts/`

Files:

- `ml/models/model_<timestamp>.joblib`
- `ml/artifacts/metrics_<timestamp>.json`
- `ml/artifacts/feature_importances_<timestamp>.json`
- optional `ml/models/prophet/*.joblib`

## 13.4 Optional DB persistence for models

Table:

- `ml_models`

Stores:

- model path
- model type
- training timestamp
- feature count
- train/test row counts
- metrics
- artifact paths

Does not store:

- raw joblib binary itself

---

## 14. Prediction Layer

Prediction generation is coordinated in:

- `pipeline/runner.py`

Method:

- load latest model artifact
- load latest feature row per technology
- generate class and growth predictions
- write latest prediction artifacts
- optionally persist prediction rows to PostgreSQL

On-disk outputs:

- `feature_store/predictions_latest.parquet`
- `feature_store/predictions_latest.json`
- `feature_store/pipeline_summary_latest.json`

Optional DB persistence:

- `predictions`

Stored per technology:

- `run_id`
- `tech`
- `prediction_date`
- `trend_class`
- `confidence`
- `predicted_growth`
- `input_feature_date`
- `model_id`
- `prediction_payload`

---

## 15. UI/API Pipeline Runner

Main file:

- `pipeline/runner.py`

Purpose:

- wrap the local pipeline into a UI/API-triggerable run
- maintain live run state
- expose stage-by-stage progress
- write file-based state
- optionally persist run/stage metadata to PostgreSQL in real time

## 15.1 Main classes and files

- `PipelineStore`
- `PipelineRunner`
- `.state/pipeline_current.json`
- `.state/pipeline_runs.json`

## 15.2 Stage sequence

Defined in `STAGE_DEFINITIONS`:

1. Raw data collection
2. Data validation
3. Data cleaning
4. Data normalization/scaling
5. Feature engineering
6. Feature selection
7. Train/test split
8. Model training
9. Model evaluation
10. Prediction/forecast generation
11. Final output creation
12. Dashboard refresh

## 15.3 What the runner tracks

Per run:

- run ID
- status
- overall progress
- current stage
- timings
- records processed
- features created
- model score
- error
- parameters
- metrics
- dataset dimensions
- feature tracking
- ML tracking
- logs
- all stages

Per stage:

- stage name
- status
- progress
- start / end / duration
- records processed
- inserted / rejected / duplicates
- missing / outliers
- input shape
- output shape
- error details
- metadata payload

## 15.4 File-based state

Used for durability and fallback:

- `.state/pipeline_current.json`
- `.state/pipeline_runs.json`

## 15.5 Optional DB persistence

Tables:

- `pipeline_runs`
- `pipeline_stages`

`pipeline_runs` stores run-level summary.

`pipeline_stages` stores stage-level details.

The system currently keeps both:

- DB-backed run history
- file-based fallback run history

---

## 16. Database Layer

Main files:

- `db/session.py`
- `db/base.py`
- `db/models.py`
- `db/repositories.py`
- `db/init_db.py`

Migration system:

- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/*`

ORM:

- SQLAlchemy 2.x style

Database:

- PostgreSQL

## 16.1 Table list

### `pipeline_runs`

One row per pipeline execution.

### `pipeline_stages`

One row per stage per run.

Relation:

- `pipeline_stages.run_id -> pipeline_runs.id`

### `normalized_records`

Processed normalized rows after local/S3 processing.

Relation:

- optional `run_id -> pipeline_runs.id`

### `daily_features`

Engineered daily feature rows.

Relation:

- optional `run_id -> pipeline_runs.id`

### `feature_snapshots`

Snapshot metadata for a generated feature artifact.

Relation:

- optional `run_id -> pipeline_runs.id`

### `ml_models`

Metadata about trained models.

Relation:

- optional `run_id -> pipeline_runs.id`

### `predictions`

Prediction records per technology.

Relations:

- optional `run_id -> pipeline_runs.id`
- optional `model_id -> ml_models.id`

### `data_sources_summary`

Source-level counts and dimensions for a run.

Relation:

- optional `run_id -> pipeline_runs.id`

## 16.2 DB repository responsibilities

`db/repositories.py` handles:

- create/update pipeline runs
- upsert pipeline stages
- insert normalized records in batches
- upsert source summaries
- insert feature rows
- create feature snapshots
- create ML model metadata rows
- insert predictions
- query latest run / run detail / run history
- query latest features / latest model / predictions / trends

## 16.3 DB-first read behavior

The API prefers PostgreSQL first.

If DB is unavailable or empty, it falls back to local file artifacts and `.state`.

---

## 17. API Layer

Main file:

- `api/app.py`

Framework:

- FastAPI

Purpose:

- expose pipeline controls
- expose pipeline status and run history
- expose predictions, features, source summaries, models, and trend endpoints

## 17.1 Endpoints

- `GET /health`
- `POST /pipeline/run`
- `GET /pipeline/status`
- `GET /pipeline/runs`
- `GET /pipeline/runs/{run_id}`
- `GET /pipeline/runs/{run_id}/logs`
- `GET /pipeline/metrics`
- `GET /pipeline/predictions/latest`
- `GET /sources/summary`
- `GET /sources/market-context`
- `GET /trends/top`
- `GET /trends/history/{name}`
- `GET /features/{name}`
- `GET /technology/{name}`
- `GET /models/latest`
- `GET /forecast/{name}`

## 17.2 API data sourcing rules

### DB-first endpoints

These try PostgreSQL first:

- pipeline status
- pipeline runs
- pipeline run detail
- latest predictions
- top trends
- trend history
- latest feature for a technology
- latest model
- source summary

### File fallback

If DB data is unavailable, the API falls back to:

- `.state/*.json`
- `feature_store/features_all.parquet`
- `feature_store/predictions_latest.json`
- local model/joblib artifacts

---

## 18. Dashboard Layer

Main file:

- `dashboard/streamlit_app.py`

Framework:

- Streamlit

Purpose:

- act as the UI control center for the pipeline and analytics

The dashboard does not run the pipeline directly itself.

It calls FastAPI.

## 18.1 Main dashboard tabs

- `Pipeline Control`
- `Live Insights`
- `Feature Layer`
- `ML & Predictions`
- `Run History`
- `Market Trends`

## 18.2 UI behaviors

- can trigger `Run Full Pipeline`
- tracks live stage progress
- shows run history
- shows feature and ML metrics
- shows predictions
- renders trend charts

## 18.3 API URL behavior

Default API URL:

- `http://127.0.0.1:8001`

Fallback logic:

- if `8001` fails, try `8000`
- if `8000` fails, try `8001`

---

## 19. File-Based Pipeline State

Directory:

- `.state/`

Files:

- `.state/pipeline_current.json`
- `.state/pipeline_runs.json`

Purpose:

- current run status
- recent run history
- fallback source if DB is unavailable

Retention:

- `pipeline_runs.json` keeps recent runs only
- logs are capped in runner logic

---

## 20. Generated Artifact Inventory

## 20.1 Raw generated local data

Location:

- `Data/`
- `Data/market_intel/`

Generated by:

- `scripts/generate_market_intel_dataset.py`

## 20.2 Processed data

Location:

- `processed/`

Generated by:

- `processing/local_processor.py`
- `processing/processor.py`

## 20.3 Feature artifacts

Location:

- `feature_store/`

Generated by:

- `feature_store/engineer.py`

## 20.4 Model artifacts

Location:

- `ml/models/`
- `ml/artifacts/`

Generated by:

- `ml/train.py`

## 20.5 Prediction artifacts

Location:

- `feature_store/predictions_latest.parquet`
- `feature_store/predictions_latest.json`
- `feature_store/pipeline_summary_latest.json`

Generated by:

- `pipeline/runner.py`

## 20.6 Import helper files

Location:

- `imports/`

Generated by:

- `scripts/generate_market_intel_dataset.py`

## 20.7 Sample payloads

Location:

- `samples/api/`
- `samples/json/`

Generated by:

- `scripts/generate_market_intel_dataset.py`

---

## 21. Commands and Entry Points

## 21.1 Data generation

```powershell
python -m scripts.generate_market_intel_dataset
```

## 21.2 Local CLI pipeline

```powershell
python -m scripts.run_pipeline --clean
```

## 21.3 UI/API pipeline runner

```powershell
python -m pipeline.runner
```

## 21.4 FastAPI

```powershell
uvicorn api.app:app --host 127.0.0.1 --port 8001
```

or

```powershell
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

## 21.5 Streamlit

```powershell
streamlit run dashboard/streamlit_app.py
```

## 21.6 Backfill DB from existing artifacts

```powershell
python -m scripts.backfill_db_from_existing_artifacts
python -m scripts.backfill_db_from_existing_artifacts --store-normalized-records
```

## 21.7 Producers / streaming

```powershell
python main.py --all
python main.py --consumer
python main.py --s3-raw-consumer
```

---

## 22. Data Ownership: Disk vs Database

## 22.1 Disk-only raw/generated boundary

These stay file-based:

- `Data/*.csv`
- `Data/market_intel/*.csv`
- raw generated parquet variants under `Data/`
- `imports/*`
- generated samples

## 22.2 Disk + DB derived layers

These exist on disk and may also be mirrored into PostgreSQL:

- `processed/`
- `feature_store/features_all.parquet`
- `feature_store/features/<tech>/latest.parquet`
- `ml/models/*.joblib`
- `ml/artifacts/*.json`
- `feature_store/predictions_latest.*`
- `.state/*.json`

DB stores metadata and queryable records for these derived layers.

---

## 23. Current Source-of-Truth Rules

The system is hybrid.

### For raw/local sample inputs

Source of truth:

- local files in `Data/`

### For normalized processed data

Operational source:

- parquet in `processed/`

Optional DB mirror:

- `normalized_records`

### For features

Operational source:

- `feature_store/features_all.parquet`

Optional DB mirror:

- `daily_features`

### For models

Operational source:

- joblib on disk

Optional DB metadata mirror:

- `ml_models`

### For predictions

Operational source:

- latest prediction files on disk

Optional DB mirror:

- `predictions`

### For pipeline run history

Current active preference:

- PostgreSQL first
- `.state` fallback

---

## 24. Cleanup Behavior

When `clean=true` for a full pipeline run:

Local derived outputs cleaned:

- `processed/`
- `feature_store/features/`
- `feature_store/features_all.parquet`
- `feature_store/feature_index.json`
- `feature_store/predictions_latest.parquet`
- `feature_store/predictions_latest.json`
- `feature_store/pipeline_summary_latest.json`

Not cleaned by default:

- raw `Data/`
- `imports/`
- `ml/models/` historical models
- `ml/artifacts/` historical metrics/importances
- historical DB runs and model metadata

Optional DB cleanup behavior:

- controlled by `CLEAN_DB_LATEST_ONLY`

---

## 25. Real-Time DB Persistence During UI Runs

For the current fixed implementation:

When a pipeline run is triggered from UI or API:

1. a `pipeline_runs` row is created immediately
2. `pipeline_stages` are upserted as stages start and complete
3. normalized processed rows can be inserted into `normalized_records`
4. source summaries are inserted into `data_sources_summary`
5. engineered features are inserted into `daily_features`
6. snapshot metadata is inserted into `feature_snapshots`
7. model metadata is inserted into `ml_models`
8. predictions are inserted into `predictions`
9. API and dashboard can read those rows while or after the run completes

This depends on:

- `.env` enabling DB persistence
- the currently running API/backend process being restarted after config/code changes

---

## 26. Important Files by Responsibility

### Core runtime

- `config/settings.py`
- `pipeline/runner.py`
- `api/app.py`
- `dashboard/streamlit_app.py`

### Local data path

- `scripts/generate_market_intel_dataset.py`
- `processing/local_processor.py`
- `processing/schemas.py`
- `feature_store/engineer.py`
- `ml/train.py`

### Database

- `db/models.py`
- `db/repositories.py`
- `db/session.py`
- `alembic/env.py`
- `alembic/versions/*`

### Streaming path

- `main.py`
- `producers/*.py`
- `consumers/s3_raw_consumer.py`
- `processing/processor.py`

### Docs / operations

- `README.md`
- `RUNBOOK.md`
- `DATA_GENERATION_RUNBOOK.md`
- `PROJECT_FLOW.md`
- `CURRENT_ARCHITECTURE.md`

---

## 27. Relationship Summary

### File and module relations

```text
generate_market_intel_dataset.py
  -> Data/
  -> imports/
  -> samples/

LocalProcessor
  -> reads Data/
  -> writes processed/
  -> optional DB: normalized_records, data_sources_summary

FeatureEngineer
  -> reads processed/
  -> writes feature_store/
  -> optional DB: daily_features, feature_snapshots

ModelTrainer
  -> reads feature_store/features_all.parquet
  -> writes ml/models/, ml/artifacts/
  -> optional DB: ml_models

PipelineRunner
  -> orchestrates all stages
  -> writes .state/
  -> writes latest predictions/summary files
  -> optional DB: pipeline_runs, pipeline_stages, predictions

FastAPI
  -> reads DB first
  -> falls back to files/.state

Streamlit
  -> reads/writes only through FastAPI
```

### DB relations

```text
pipeline_runs
  1 -> many pipeline_stages
  1 -> many normalized_records (optional)
  1 -> many daily_features (optional)
  1 -> many feature_snapshots (optional)
  1 -> many ml_models (optional)
  1 -> many predictions (optional)
  1 -> many data_sources_summary (optional)

ml_models
  1 -> many predictions (optional)
```

---

## 28. Current Reality Summary

The current system is a hybrid local analytics stack with:

- generated but realistic sample data
- offline processing into normalized parquet
- feature engineering into a local feature store
- ML training and prediction generation on top of those features
- a UI/API-triggerable pipeline runner
- live stage tracking
- optional but working PostgreSQL persistence for derived layers
- FastAPI and Streamlit on top of either DB-first reads or file fallback

In short:

```text
local generated data
-> processed parquet
-> feature parquet
-> ML artifacts
-> latest predictions
-> PostgreSQL mirrors for derived layers
-> FastAPI
-> Streamlit
```

---

## 29. Safe Refactor Additions

The latest architecture cleanup intentionally avoids moving public entrypoints
or generated artifact paths. Instead, it adds compatibility-safe layers around
the existing working flow.

### 29.1 Domain contracts

New package:

```text
domain/
  __init__.py
  artifacts.py
  pipeline.py
```

Purpose:

- define storage-agnostic contracts for pipeline runs, pipeline stages,
  normalized records, feature snapshots, model metadata, predictions, and
  source summaries
- keep stage definitions in one domain-level constant:
  `PIPELINE_STAGE_DEFINITIONS`
- avoid coupling API, DB, dashboard, and file code to one another

Current usage:

- `pipeline/runner.py` imports `PIPELINE_STAGE_DEFINITIONS`
- tests validate stage definition stability and shape contracts

### 29.2 Infrastructure storage adapter

New package:

```text
infrastructure/
  __init__.py
  storage/
    __init__.py
    json_store.py
    pipeline_state.py
```

Purpose:

- centralize JSON state-file reading/writing
- preserve existing files:
  - `.state/pipeline_current.json`
  - `.state/pipeline_runs.json`
- keep corrupt/missing state-file fallback behavior
- use atomic replace writes for JSON state updates

Current usage:

- `PipelineStore` still exists in `pipeline/runner.py`
- API and CLI callers still use the same runner/store API
- internally, `PipelineStore` now delegates to
  `PipelineStateFileRepository`

### 29.3 Prediction service

New package:

```text
prediction/
  __init__.py
  service.py
```

Purpose:

- separate latest-prediction generation from pipeline orchestration
- keep the existing output files unchanged:
  - `feature_store/predictions_latest.parquet`
  - `feature_store/predictions_latest.json`
- keep optional DB insertion into `predictions`
- keep `PipelineRunner._generate_predictions()` as a compatibility wrapper

Current usage:

- `PipelineRunner._generate_predictions()` calls
  `PredictionService.generate_latest_predictions()`
- response keys remain compatible with the previous runner output

### 29.4 Why this refactor is intentionally small

The project has many runtime paths:

- CLI pipeline commands
- UI/API-triggered pipeline runs
- local file fallback
- optional PostgreSQL persistence
- optional Kafka/S3 streaming path
- generated artifact compatibility

Large file moves or endpoint rewrites could break working behavior. The safe
approach is to introduce stable contracts and adapters first, then migrate
callers gradually.

### 29.5 Skipped risky changes

These were not applied because they are larger and need broader regression
testing:

- moving `db/` into `infrastructure/db/`
- splitting `api/app.py` endpoints into multiple routers
- moving processing schema logic between local and streaming processors
- changing feature artifact layout or model artifact layout
- changing API response shapes
- replacing `.state` JSON fallback with DB-only state
- renaming commands, endpoint paths, DB tables, or generated artifact paths
