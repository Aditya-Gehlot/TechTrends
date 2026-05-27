Data generation runbook for TechTrends

Prerequisites
- Python 3.9+ (recommended)
- Git
- Optional: PostgreSQL client (`psql`), MongoDB tools (`mongoimport`), Elasticsearch (`curl`/bulk API)

Quickstart

1. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Generate datasets (example):

```powershell
python -u scripts/generate_market_intel_dataset.py --min-rows 100000 --formats csv parquet ndjson es --scale 1 --seed 20260526
```

Flags
- `--min-rows`: minimum total rows across all generated datasets (script will rescale counts up if needed)
- `--scale`: initial multiplier for Poisson/sample generation (can be fractional)
- `--seed`: RNG seed for deterministic output
- `--formats`: space-separated list of output formats; supported: `csv`, `parquet`, `ndjson`, `es`

Outputs
- CSV and Parquet files are written to `Data/` and `Data/market_intel/`.
- NDJSON (newline-delimited JSON) and Elasticsearch bulk NDJSON files are written to `imports/`.
- Machine-readable JSON schemas: `Data/market_intel/schemas/`
- SQL seed helper: `imports/seed_load.sql`
- Validation report: `imports/validation_report.json`
- Dataset catalog: `Data/market_intel/DATASET_CATALOG.md`

Ingest into PostgreSQL (example using psql client)

- Edit `imports/seed_load.sql` if needed, then run:

```powershell
# using psql client; set PGHOST/PGUSER/PGDATABASE or pass connection args
psql -f imports/seed_load.sql
```

Or run psql `\copy` commands interactively:

```sql
\copy techtrends.companies FROM 'Data/market_intel/companies.csv' CSV HEADER;
\copy techtrends.linkedin_jobs FROM 'Data/linkedin_jobs.csv' CSV HEADER;
```

Ingest into MongoDB (example):

```powershell
mongoimport --db techtrends_market_intel --collection companies --type csv --headerline --file "Data/market_intel/companies.csv"
mongoimport --db techtrends_market_intel --collection twitter_stream --type json --file imports/twitter_stream.ndjson
```

Index into Elasticsearch (example):

```powershell
# create index (adjust mappings as needed)
curl -XPUT "http://localhost:9200/techtrends-twitter" -H 'Content-Type: application/json' -d '{}'
# bulk load (replace file path)
curl -H "Content-Type: application/x-ndjson" -XPOST "http://localhost:9200/techtrends-twitter/_bulk" --data-binary "@imports/twitter_stream.es.bulk.ndjson"
```

Notes
- The generator is deterministic when you set `--seed`.
- If you need smaller test datasets, lower `--min-rows` and `--scale`.
- Check `imports/validation_report.json` after generation for integrity warnings.

Contact
- For improvements or adjustments, open an issue or request changes to `scripts/generate_market_intel_dataset.py`.
