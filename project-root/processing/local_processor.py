"""Local CSV processing pipeline.

Reads CSV datasets from the project's `Data/` folder, normalizes rows into
a common schema, deduplicates, and writes Parquet files partitioned by
source/year/month/day under `processed/`.

This is the offline, dataset-driven ingestion path used for demo and ML.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from config import settings
from .schemas import NormalizedRecord

logger = logging.getLogger(__name__)


class LocalProcessor:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir or (Path(settings.BASE_DIR) / "Data"))
        if not self.data_dir.exists():
            raise ValueError(f"Data directory not found: {self.data_dir}")

    def _write_partitioned(self, df: pd.DataFrame, source: str, ts_col: str = "timestamp") -> int:
        if df.empty:
            return 0
        # ensure timestamp is datetime
        df[ts_col] = pd.to_datetime(df[ts_col])
        written = 0
        for date, g in df.groupby(df[ts_col].dt.date):
            dt = pd.to_datetime(date)
            year = dt.strftime("%Y")
            month = dt.strftime("%m")
            day = dt.strftime("%d")
            dest_dir = settings.PROCESSED_DIR / source / year / month / day
            dest_dir.mkdir(parents=True, exist_ok=True)
            out_path = dest_dir / f"{date}.parquet"
            try:
                # write deterministic per-day file (idempotent)
                g.to_parquet(out_path, index=False, engine="pyarrow")
                written += len(g)
                logger.info("Wrote %d records to %s", len(g), out_path)
            except Exception:
                logger.exception("Failed to write parquet to %s", out_path)
        return written

    def _clean_split_list(self, s: Any) -> List[str]:
        if pd.isna(s):
            return []
        if isinstance(s, list):
            return [str(x).strip() for x in s if x]
        try:
            parts = [p.strip() for p in str(s).split(",")]
            return [p for p in parts if p]
        except Exception:
            return [str(s).strip()]

    def process_linkedin(self) -> int:
        path = self.data_dir / "linkedin_jobs.csv"
        if not path.exists():
            return 0
        df = pd.read_csv(path, parse_dates=["posted_at"], keep_default_na=True)
        # drop malformed rows
        df = df.dropna(subset=["job_id", "posted_at"]) 
        df = df.drop_duplicates(subset=["job_id"])

        rows = []
        for _, r in df.iterrows():
            techs = self._clean_split_list(r.get("skills"))
            rec = NormalizedRecord(
                source="linkedin_jobs",
                id=str(r.get("job_id")),
                timestamp=r.get("posted_at") if not pd.isna(r.get("posted_at")) else datetime.now(timezone.utc),
                title=str(r.get("role")) if not pd.isna(r.get("role")) else None,
                text=str(r.get("job_description")) if not pd.isna(r.get("job_description")) else None,
                tags=techs,
                url=None,
                techs=techs,
                raw={k: (None if pd.isna(v) else v) for k, v in r.to_dict().items()},
            )
            rows.append(rec.dict())

        out_df = pd.DataFrame(rows)
        return self._write_partitioned(out_df, "linkedin_jobs")

    def process_twitter(self) -> int:
        path = self.data_dir / "twitter_stream.csv"
        if not path.exists():
            return 0
        df = pd.read_csv(path, parse_dates=["created_at"], keep_default_na=True)
        df = df.dropna(subset=["tweet_id", "created_at"]).drop_duplicates(subset=["tweet_id"]) 
        rows = []
        for _, r in df.iterrows():
            tech = r.get("tech_topic")
            techs = [str(tech).strip()] if pd.notna(tech) else []
            payload = r.to_dict()
            # compute engagement score
            try:
                engagement = int(r.get("likes", 0)) + int(r.get("retweets", 0))
            except Exception:
                engagement = 0
            payload["engagement_score"] = engagement
            rec = NormalizedRecord(
                source="twitter",
                id=str(r.get("tweet_id")),
                timestamp=r.get("created_at"),
                title=None,
                text=str(r.get("content")) if not pd.isna(r.get("content")) else None,
                tags=[str(r.get("sentiment"))] if pd.notna(r.get("sentiment")) else [],
                url=None,
                techs=techs,
                raw=payload,
            )
            rows.append(rec.dict())

        out_df = pd.DataFrame(rows)
        return self._write_partitioned(out_df, "twitter")

    def process_github(self) -> int:
        path = self.data_dir / "github_events.csv"
        if not path.exists():
            return 0
        df = pd.read_csv(path, parse_dates=["event_time"], keep_default_na=True)
        df = df.dropna(subset=["event_id", "event_time"]).drop_duplicates(subset=["event_id"]) 
        rows = []
        for _, r in df.iterrows():
            tech = r.get("topic") or r.get("language")
            techs = [str(tech).strip()] if pd.notna(tech) else []
            payload = r.to_dict()
            rec = NormalizedRecord(
                source="github",
                id=str(r.get("event_id")),
                timestamp=r.get("event_time"),
                title=None,
                text=f"{r.get('repository')} {r.get('topic')}",
                tags=[r.get("language")] if pd.notna(r.get("language")) else [],
                url=None,
                techs=techs,
                raw=payload,
            )
            rows.append(rec.dict())

        out_df = pd.DataFrame(rows)
        return self._write_partitioned(out_df, settings.GITHUB_TOPIC)

    def process_blogs(self) -> int:
        path = self.data_dir / "tech_blogs.csv"
        if not path.exists():
            return 0
        df = pd.read_csv(path, parse_dates=["published_at"], keep_default_na=True)
        df = df.dropna(subset=["article_id", "published_at"]).drop_duplicates(subset=["article_id"]) 
        rows = []
        for _, r in df.iterrows():
            tech = r.get("topic")
            techs = [str(tech).strip()] if pd.notna(tech) else []
            payload = r.to_dict()
            rec = NormalizedRecord(
                source="blogs",
                id=str(r.get("article_id")),
                timestamp=r.get("published_at"),
                title=str(r.get("title")) if pd.notna(r.get("title")) else None,
                text=str(r.get("summary")) if pd.notna(r.get("summary")) else None,
                tags=[],
                url=None,
                techs=techs,
                raw=payload,
            )
            rows.append(rec.dict())

        out_df = pd.DataFrame(rows)
        return self._write_partitioned(out_df, settings.BLOG_TOPIC)

    def process_stackoverflow(self) -> int:
        path = self.data_dir / "stackoverflow_questions.csv"
        if not path.exists():
            return 0
        df = pd.read_csv(path, parse_dates=["created_at"], keep_default_na=True)
        df = df.dropna(subset=["question_id", "created_at"]).drop_duplicates(subset=["question_id"]) 
        rows = []
        for _, r in df.iterrows():
            tag = r.get("tag")
            techs = [str(tag).strip()] if pd.notna(tag) else []
            payload = r.to_dict()
            rec = NormalizedRecord(
                source="stackoverflow",
                id=str(r.get("question_id")),
                timestamp=r.get("created_at"),
                title=str(r.get("title")) if pd.notna(r.get("title")) else None,
                text=str(r.get("body_preview")) if pd.notna(r.get("body_preview")) else None,
                tags=techs,
                url=None,
                techs=techs,
                raw=payload,
            )
            rows.append(rec.dict())

        out_df = pd.DataFrame(rows)
        return self._write_partitioned(out_df, settings.STACKOVERFLOW_TOPIC)

    def process_google_trends(self) -> int:
        path = self.data_dir / "google_trends.csv"
        if not path.exists():
            return 0
        df = pd.read_csv(path, parse_dates=["date"], keep_default_na=True)
        df = df.dropna(subset=["keyword", "date"]).drop_duplicates()
        rows = []
        for _, r in df.iterrows():
            keyword = r.get("keyword")
            techs = [str(keyword).strip()] if pd.notna(keyword) else []
            payload = r.to_dict()
            rec = NormalizedRecord(
                source="google_trends",
                id=f"{r.get('date').date()}-{keyword}",
                timestamp=r.get("date"),
                title=None,
                text=None,
                tags=[],
                url=None,
                techs=techs,
                raw=payload,
            )
            rows.append(rec.dict())

        out_df = pd.DataFrame(rows)
        return self._write_partitioned(out_df, settings.GOOGLE_TRENDS_TOPIC)

    def run_all(self) -> Dict[str, int]:
        results = {}
        results["linkedin_jobs"] = self.process_linkedin()
        results["twitter"] = self.process_twitter()
        results[settings.GITHUB_TOPIC] = self.process_github()
        results[settings.BLOG_TOPIC] = self.process_blogs()
        results[settings.STACKOVERFLOW_TOPIC] = self.process_stackoverflow()
        results[settings.GOOGLE_TRENDS_TOPIC] = self.process_google_trends()
        logger.info("Local processing results: %s", results)
        return results


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL)
    lp = LocalProcessor()
    lp.run_all()
