"""Local generated-data processing pipeline.

Reads the CSV datasets generated into the project's ``Data/`` folder,
normalizes event-like rows into the shared ``NormalizedRecord`` schema, and
writes analytics-ready Parquet partitioned by source/date under ``processed/``.

This is the offline sample-data path used by the feature, ML, API, and
dashboard layers.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd

from config import settings
from .schemas import NormalizedRecord

logger = logging.getLogger(__name__)

try:
    from db import repositories as db_repo
except Exception:  # pragma: no cover - DB support is optional at runtime
    db_repo = None


class LocalProcessor:
    """Normalize generated local CSV datasets into processed Parquet files."""

    DATASET_CONFIGS: Sequence[Dict[str, Any]] = (
        {
            "path": "linkedin_jobs.csv",
            "source": "linkedin_jobs",
            "id_col": "job_id",
            "timestamp_col": "posted_at",
            "topic_cols": ("tech_category",),
            "tech_list_cols": ("skills",),
            "title_col": "role",
            "text_col": "job_description",
            "tag_cols": ("skills",),
        },
        {
            "path": "twitter_stream.csv",
            "source": "twitter_stream",
            "id_col": "tweet_id",
            "timestamp_col": "created_at",
            "topic_cols": ("tech_topic",),
            "title_col": None,
            "text_col": "content",
            "tag_cols": ("sentiment", "hashtags"),
        },
        {
            "path": "github_events.csv",
            "source": "github_events",
            "id_col": "event_id",
            "timestamp_col": "event_time",
            "topic_cols": ("topic",),
            "title_col": "repository",
            "text_col": "event_type",
            "tag_cols": ("language",),
        },
        {
            "path": "tech_blogs.csv",
            "source": "tech_blogs",
            "id_col": "article_id",
            "timestamp_col": "published_at",
            "topic_cols": ("topic",),
            "title_col": "title",
            "text_col": "summary",
            "tag_cols": ("hashtags",),
        },
        {
            "path": "stackoverflow_questions.csv",
            "source": "stackoverflow_questions",
            "id_col": "question_id",
            "timestamp_col": "created_at",
            "topic_cols": ("tag",),
            "title_col": "title",
            "text_col": "body_preview",
            "tag_cols": ("tag",),
        },
        {
            "path": "google_trends.csv",
            "source": "google_trends",
            "id_col": None,
            "timestamp_col": "date",
            "topic_cols": ("keyword",),
            "title_col": None,
            "text_col": None,
            "tag_cols": ("region", "country"),
            "dedupe_cols": ("date", "keyword", "region", "country"),
        },
        {
            "path": "market_intel/reddit_discussions.csv",
            "source": "reddit_discussions",
            "id_col": "reddit_post_id",
            "timestamp_col": "created_at",
            "topic_cols": ("topic",),
            "title_col": "title",
            "text_col": "body",
            "tag_cols": ("subreddit", "hashtags"),
        },
        {
            "path": "market_intel/hackernews_posts.csv",
            "source": "hackernews_posts",
            "id_col": "hn_post_id",
            "timestamp_col": "created_at",
            "topic_cols": ("topic",),
            "title_col": "title",
            "text_col": "ai_summary",
            "tag_cols": ("domain",),
            "url_col": "source_reference",
        },
        {
            "path": "market_intel/youtube_ai_content.csv",
            "source": "youtube_ai_content",
            "id_col": "video_id",
            "timestamp_col": "published_at",
            "topic_cols": ("topic",),
            "title_col": "title",
            "text_col": "ai_summary",
            "tag_cols": ("channel", "hashtags"),
            "url_col": "source_reference",
        },
        {
            "path": "market_intel/startup_funding.csv",
            "source": "startup_funding",
            "id_col": "funding_event_id",
            "timestamp_col": "announced_at",
            "topic_cols": ("tech_category",),
            "title_col": "company",
            "text_col": "lead_investor",
            "tag_cols": ("round_type",),
            "url_col": "source_reference",
        },
        {
            "path": "market_intel/producthunt_launches.csv",
            "source": "producthunt_launches",
            "id_col": "launch_id",
            "timestamp_col": "launched_at",
            "topic_cols": ("topic",),
            "title_col": "product_name",
            "text_col": "ai_summary",
            "tag_cols": ("category",),
            "url_col": "source_reference",
        },
        {
            "path": "market_intel/news_media_mentions.csv",
            "source": "news_media_mentions",
            "id_col": "mention_id",
            "timestamp_col": "published_at",
            "topic_cols": ("topic",),
            "title_col": "headline",
            "text_col": "ai_summary",
            "tag_cols": ("source", "hashtags"),
            "url_col": "source_reference",
        },
        {
            "path": "market_intel/kaggle_ml_activity.csv",
            "source": "kaggle_ml_activity",
            "id_col": "kaggle_activity_id",
            "timestamp_col": "activity_date",
            "topic_cols": ("topic",),
            "title_col": "competition_name",
            "text_col": "ai_summary",
            "tag_cols": ("country",),
            "url_col": "source_reference",
        },
    )

    EVENT_SOURCES = tuple(c["source"] for c in DATASET_CONFIGS) + ("market_events",)

    def __init__(self, data_dir: Path | str | None = None, run_id: str | None = None):
        self.data_dir = Path(data_dir or (Path(settings.BASE_DIR) / "Data"))
        self.run_id = run_id
        if not self.data_dir.exists():
            raise ValueError(f"Data directory not found: {self.data_dir}")

    def _write_partitioned(self, df: pd.DataFrame, source: str, ts_col: str = "timestamp") -> int:
        if df.empty:
            return 0

        df = df.copy()
        df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
        df = df.dropna(subset=[ts_col])
        if df.empty:
            return 0

        written = 0
        file_count = 0
        min_date = None
        max_date = None
        for date, g in df.groupby(df[ts_col].dt.date):
            dt = pd.to_datetime(date)
            dest_dir = settings.PROCESSED_DIR / source / dt.strftime("%Y") / dt.strftime("%m") / dt.strftime("%d")
            dest_dir.mkdir(parents=True, exist_ok=True)
            out_path = dest_dir / f"{date}.parquet"
            g.to_parquet(out_path, index=False, engine="pyarrow")
            if db_repo is not None:
                db_repo.insert_normalized_records_batch(
                    g.to_dict(orient="records"),
                    external_run_id=self.run_id,
                    processed_file_path=str(out_path),
                )
            written += len(g)
            file_count += 1
            min_date = date if min_date is None or date < min_date else min_date
            max_date = date if max_date is None or date > max_date else max_date

        logger.info("Processed %-24s rows=%d partitions=%d", source, written, file_count)
        if db_repo is not None:
            db_repo.upsert_data_source_summary(
                source=source,
                external_run_id=self.run_id,
                file_count=file_count,
                row_count=written,
                column_count=int(df.shape[1]),
                min_date=min_date,
                max_date=max_date,
                output_path=str(settings.PROCESSED_DIR / source),
                metadata={"format": "parquet", "partitioning": "source/year/month/day"},
            )
        return written

    def _write_dimension(self, df: pd.DataFrame, name: str) -> int:
        if df.empty:
            return 0
        dest_dir = settings.PROCESSED_DIR / "_dimensions"
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_path = dest_dir / f"{name}.parquet"
        df.to_parquet(out_path, index=False, engine="pyarrow")
        logger.info("Processed dimension %-16s rows=%d", name, len(df))
        if db_repo is not None:
            db_repo.upsert_data_source_summary(
                source=f"{name}_dimension",
                external_run_id=self.run_id,
                file_count=1,
                row_count=int(len(df)),
                column_count=int(df.shape[1]),
                output_path=str(out_path),
                metadata={"format": "parquet", "dimension": True},
            )
        return len(df)

    def _clean_split_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        try:
            if pd.isna(value):
                return []
        except Exception:
            pass
        if isinstance(value, (list, tuple, set, np.ndarray)):
            return [str(x).strip() for x in value if str(x).strip()]

        text = str(value).strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                loaded = json.loads(text)
                if isinstance(loaded, list):
                    return [str(x).strip() for x in loaded if str(x).strip()]
            except Exception:
                pass

        delimiter = "|" if "|" in text and "," not in text else ","
        return [part.strip() for part in text.split(delimiter) if part.strip()]

    def _append_values(self, values: List[str], candidates: Iterable[Any]) -> None:
        seen = {v.casefold() for v in values}
        for candidate in candidates:
            for item in self._clean_split_list(candidate):
                key = item.casefold()
                if key not in seen:
                    values.append(item)
                    seen.add(key)

    def _native_value(self, value: Any) -> Any:
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if isinstance(value, np.generic):
            return value.item()
        return value

    def _raw_dict(self, row: pd.Series) -> Dict[str, Any]:
        return {str(k): self._native_value(v) for k, v in row.to_dict().items()}

    def _record_dict(self, record: NormalizedRecord) -> Dict[str, Any]:
        if hasattr(record, "model_dump"):
            return record.model_dump()
        return record.dict()

    def _source_path(self, relative_path: str) -> Path:
        return self.data_dir / Path(relative_path)

    def _make_id(self, source: str, row: pd.Series, config: Dict[str, Any]) -> str:
        id_col = config.get("id_col")
        if id_col and id_col in row and pd.notna(row.get(id_col)):
            return str(row.get(id_col))

        parts = [source]
        for col in config.get("dedupe_cols") or (config["timestamp_col"], *config.get("topic_cols", ())):
            if col in row:
                parts.append(str(row.get(col)))
        return "|".join(parts)

    def _process_config(self, config: Dict[str, Any]) -> int:
        path = self._source_path(config["path"])
        source = config["source"]
        if not path.exists():
            logger.warning("Skipping %-24s missing file %s", source, path)
            return 0

        timestamp_col = config["timestamp_col"]
        df = pd.read_csv(path, parse_dates=[timestamp_col], keep_default_na=True)
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")

        required = [timestamp_col]
        if config.get("id_col"):
            required.append(config["id_col"])
        df = df.dropna(subset=required)

        dedupe_cols = list(config.get("dedupe_cols") or ([config["id_col"]] if config.get("id_col") else []))
        if dedupe_cols:
            df = df.drop_duplicates(subset=dedupe_cols)
        else:
            df = df.drop_duplicates()

        rows: List[Dict[str, Any]] = []
        topic_cols = tuple(config.get("topic_cols") or ())
        tech_list_cols = tuple(config.get("tech_list_cols") or ())
        tag_cols = tuple(config.get("tag_cols") or ())
        title_col = config.get("title_col")
        text_col = config.get("text_col")
        url_col = config.get("url_col")

        for _, row in df.iterrows():
            techs: List[str] = []
            self._append_values(techs, (row.get(col) for col in topic_cols if col in row))
            self._append_values(techs, (row.get(col) for col in tech_list_cols if col in row))
            if not techs:
                continue

            tags: List[str] = []
            self._append_values(tags, (row.get(col) for col in tag_cols if col in row))

            record = NormalizedRecord(
                source=source,
                id=self._make_id(source, row, config),
                timestamp=row.get(timestamp_col) if pd.notna(row.get(timestamp_col)) else datetime.now(timezone.utc),
                title=str(row.get(title_col)) if title_col and pd.notna(row.get(title_col)) else None,
                text=str(row.get(text_col)) if text_col and pd.notna(row.get(text_col)) else None,
                tags=tags,
                url=str(row.get(url_col)) if url_col and pd.notna(row.get(url_col)) else None,
                techs=techs,
                raw=self._raw_dict(row),
            )
            rows.append(self._record_dict(record))

        return self._write_partitioned(pd.DataFrame(rows), source)

    def process_market_events(self) -> int:
        path = self._source_path("market_intel/market_events.csv")
        if not path.exists():
            logger.warning("Skipping %-24s missing file %s", "market_events", path)
            return 0

        df = pd.read_csv(path, parse_dates=["event_date"], keep_default_na=True)
        df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
        df = df.dropna(subset=["event_id", "event_date"]).drop_duplicates(subset=["event_id"])

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            try:
                impacts = json.loads(str(row.get("topic_impacts") or "{}"))
            except Exception:
                logger.warning("Could not parse topic impacts for %s", row.get("event_id"))
                impacts = {}

            for topic, impact in impacts.items():
                topic_name = str(topic).strip()
                if not topic_name:
                    continue
                raw = self._raw_dict(row)
                raw["topic"] = topic_name
                raw["impact_score"] = self._native_value(impact)
                record = NormalizedRecord(
                    source="market_events",
                    id=f"{row.get('event_id')}|{topic_name}",
                    timestamp=row.get("event_date") if pd.notna(row.get("event_date")) else datetime.now(timezone.utc),
                    title=str(row.get("title")) if pd.notna(row.get("title")) else None,
                    text=str(row.get("title")) if pd.notna(row.get("title")) else None,
                    tags=["market_event"],
                    url=None,
                    techs=[topic_name],
                    raw=raw,
                )
                rows.append(self._record_dict(record))

        return self._write_partitioned(pd.DataFrame(rows), "market_events")

    def process_companies_dimension(self) -> int:
        path = self._source_path("market_intel/companies.csv")
        if not path.exists():
            return 0
        df = pd.read_csv(path, keep_default_na=True)
        if "dominant_topics" in df.columns:
            df["dominant_topics_list"] = df["dominant_topics"].apply(self._clean_split_list)
        return self._write_dimension(df, "companies")

    def run_all(self) -> Dict[str, int]:
        results: Dict[str, int] = {}
        for config in self.DATASET_CONFIGS:
            results[config["source"]] = self._process_config(config)
        results["market_events"] = self.process_market_events()
        results["companies_dimension"] = self.process_companies_dimension()
        results["total_event_rows"] = sum(results.get(source, 0) for source in self.EVENT_SOURCES)
        logger.info("Local generated-data processing complete: %s", results)
        return results


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL)
    LocalProcessor().run_all()
