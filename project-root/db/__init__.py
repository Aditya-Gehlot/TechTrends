"""Database support for TechTrends.

The database layer is optional at runtime. File-based parquet/model artifacts
remain the default source of truth unless ENABLE_DB_PERSISTENCE=true and the
configured PostgreSQL database is reachable.
"""

