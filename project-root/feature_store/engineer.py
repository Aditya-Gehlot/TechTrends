"""Feature engineering pipeline that creates daily features per technology.

This module computes daily aggregates and rolling-window features (7 & 30
day) and writes them into the feature store as Parquet files partitioned by
technology/date.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from config import settings

logger = logging.getLogger(__name__)


class FeatureEngineer:
    def __init__(self, processed_dir: Path | None = None, feature_dir: Path | None = None):
        self.processed_dir = Path(processed_dir or settings.PROCESSED_DIR)
        self.feature_dir = Path(feature_dir or settings.FEATURE_STORE_DIR)

    def _load_processed(self, sources: List[str] | None = None) -> pd.DataFrame:
        parts = []
        base = self.processed_dir
        if not base.exists():
            return pd.DataFrame()

        # recursively find parquet files under processed/<source>/...
        for source_dir in base.iterdir():
            if not source_dir.is_dir():
                continue
            if sources and source_dir.name not in sources:
                continue
            for f in source_dir.rglob("*.parquet"):
                try:
                    df = pd.read_parquet(f)
                    parts.append(df)
                except Exception:
                    logger.exception("Failed to read processed parquet %s", f)

        if not parts:
            return pd.DataFrame()
        df = pd.concat(parts, ignore_index=True)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def generate_daily_features(self, window_days_list: List[int] | None = None):
        window_days_list = window_days_list or [7, 30]
        df = self._load_processed()
        if df.empty:
            logger.info("No processed data found to generate features")
            return

        if "techs" not in df.columns:
            logger.info("No techs field present in processed records")
            return

        # explode techs and normalize
        df = df.explode("techs")
        df = df[~df["techs"].isnull()]
        df["date"] = df["timestamp"].dt.date

        # counts per tech/date/source
        counts = (
            df.groupby(["techs", "date", "source"]).agg(count=("id", "count")).reset_index()
        )

        # pivot so we have source-specific columns
        pivot = counts.pivot_table(index=["techs", "date"], columns="source", values="count", fill_value=0).reset_index()
        pivot.columns.name = None

        # compute total mentions as sum of source counts
        source_cols = [c for c in pivot.columns if c not in ("techs", "date")]
        pivot["mentions"] = pivot[source_cols].sum(axis=1) if source_cols else 0

        # helper extractors for nested raw values
        def _safe_get(v, *keys, default=None):
            try:
                val = v
                for k in keys:
                    if isinstance(val, dict):
                        val = val.get(k, None)
                    else:
                        return default
                return val if val is not None else default
            except Exception:
                return default

        # LinkedIn metrics: job postings, avg salary, unique roles, skill frequency
        try:
            ln = df[df["source"].isin(["linkedin_jobs", "linkedin"])].copy()
            if not ln.empty:
                # salary extraction
                ln["salary_usd"] = ln["raw"].apply(lambda r: _safe_get(r, "salary_usd", default=None) if isinstance(r, dict) else None)
                ln["role"] = ln["raw"].apply(lambda r: _safe_get(r, "role", default=None) if isinstance(r, dict) else None)
                # explode skills
                ln["_skills"] = ln["raw"].apply(lambda r: r.get("skills") if isinstance(r, dict) else None)
                # flatten skills to rows for counting
                skills_rows = ln.explode("_skills").dropna(subset=["_skills"]).groupby(["techs", "date"]).agg(skill_count=("_skills", "count")).reset_index()
                ln_salary = ln.groupby(["techs", "date"]).agg(job_postings=("id", "count"), avg_salary=("salary_usd", lambda s: pd.to_numeric(s, errors="coerce").mean()), unique_roles=("role", lambda s: s.dropna().nunique())).reset_index()
                pivot = pivot.merge(ln_salary, left_on=["techs", "date"], right_on=["techs", "date"], how="left")
                pivot = pivot.merge(skills_rows, left_on=["techs", "date"], right_on=["techs", "date"], how="left")
            else:
                pivot["job_postings"] = 0
                pivot["avg_salary"] = None
                pivot["unique_roles"] = 0
                pivot["skill_count"] = 0
        except Exception:
            logger.exception("Failed computing LinkedIn metrics")
            pivot["job_postings"] = 0
            pivot["avg_salary"] = None
            pivot["unique_roles"] = 0
            pivot["skill_count"] = 0

        # Twitter metrics: sentiment score, engagement
        try:
            tw = df[df["source"].isin(["twitter"])].copy()
            if not tw.empty:
                def _sent_map(v):
                    if not v:
                        return 0
                    s = str(v).lower()
                    if "pos" in s:
                        return 1
                    if "neg" in s:
                        return -1
                    return 0

                tw["sentiment_score"] = tw["raw"].apply(lambda r: _sent_map(_safe_get(r, "sentiment", default=None)) if isinstance(r, dict) else 0)
                tw["engagement"] = tw["raw"].apply(lambda r: (int(_safe_get(r, "likes", 0) or 0) + int(_safe_get(r, "retweets", 0) or 0)) if isinstance(r, dict) else 0)
                tw_metrics = tw.groupby(["techs", "date"]).agg(twitter_count=("id", "count"), sentiment_avg=("sentiment_score", "mean"), engagement_sum=("engagement", "sum")).reset_index()
                pivot = pivot.merge(tw_metrics, left_on=["techs", "date"], right_on=["techs", "date"], how="left")
            else:
                pivot["twitter_count"] = 0
                pivot["sentiment_avg"] = 0
                pivot["engagement_sum"] = 0
        except Exception:
            logger.exception("Failed computing Twitter metrics")
            pivot["twitter_count"] = 0
            pivot["sentiment_avg"] = 0
            pivot["engagement_sum"] = 0

        # GitHub metrics: stars, forks, contributors
        try:
            gh = df[df["source"].isin(["github", settings.GITHUB_TOPIC])].copy()
            if not gh.empty:
                gh["stars_added"] = gh["raw"].apply(lambda r: int(_safe_get(r, "stars_added", default=0) or 0) if isinstance(r, dict) else 0)
                gh["forks_added"] = gh["raw"].apply(lambda r: int(_safe_get(r, "forks_added", default=0) or 0) if isinstance(r, dict) else 0)
                gh["actor_id"] = gh["raw"].apply(lambda r: _safe_get(r, "actor", "id", default=None) if isinstance(r, dict) else None)
                gh_metrics = gh.groupby(["techs", "date"]).agg(github_events=("id", "count"), stars_sum=("stars_added", "sum"), forks_sum=("forks_added", "sum"), contributors_n=("actor_id", lambda s: s.dropna().nunique())).reset_index()
                pivot = pivot.merge(gh_metrics, left_on=["techs", "date"], right_on=["techs", "date"], how="left")
            else:
                pivot["github_events"] = 0
                pivot["stars_sum"] = 0
                pivot["forks_sum"] = 0
                pivot["contributors_n"] = 0
        except Exception:
            logger.exception("Failed computing GitHub metrics")
            pivot["github_events"] = 0
            pivot["stars_sum"] = 0
            pivot["forks_sum"] = 0
            pivot["contributors_n"] = 0

        # StackOverflow metrics: question counts, answer rates
        try:
            so = df[df["source"].isin(["stackoverflow", settings.STACKOVERFLOW_TOPIC])].copy()
            if not so.empty:
                so_metrics = so.groupby(["techs", "date"]).agg(so_questions=("id", "count"), avg_answers=("raw", lambda s: pd.Series([_safe_get(r, "answers", default=0) for r in s]).astype(float).mean()), accepted_rate=("raw", lambda s: pd.Series([1 if _safe_get(r, "accepted_answer", default=False) else 0 for r in s]).mean())).reset_index()
                pivot = pivot.merge(so_metrics, left_on=["techs", "date"], right_on=["techs", "date"], how="left")
            else:
                pivot["so_questions"] = 0
                pivot["avg_answers"] = 0
                pivot["accepted_rate"] = 0
        except Exception:
            logger.exception("Failed computing StackOverflow metrics")
            pivot["so_questions"] = 0
            pivot["avg_answers"] = 0
            pivot["accepted_rate"] = 0

        # Google Trends metrics: trend_score average per date
        try:
            gt = df[df["source"].isin(["google_trends", settings.GOOGLE_TRENDS_TOPIC])].copy()
            if not gt.empty:
                gt["trend_score"] = gt["raw"].apply(lambda r: float(_safe_get(r, "trend_score", default=0) or 0) if isinstance(r, dict) else 0)
                gt_metrics = gt.groupby(["techs", "date"]).agg(trend_score_avg=("trend_score", "mean")).reset_index()
                pivot = pivot.merge(gt_metrics, left_on=["techs", "date"], right_on=["techs", "date"], how="left")
            else:
                pivot["trend_score_avg"] = 0
        except Exception:
            logger.exception("Failed computing Google Trends metrics")
            pivot["trend_score_avg"] = 0

        # Blogs metrics: views and publication counts
        try:
            bl = df[df["source"].isin(["blogs", settings.BLOG_TOPIC, "tech_blogs"])].copy()
            if not bl.empty:
                bl["views"] = bl["raw"].apply(lambda r: int(_safe_get(r, "views", default=0) or 0) if isinstance(r, dict) else 0)
                bl_metrics = bl.groupby(["techs", "date"]).agg(blog_posts=("id", "count"), blog_views_avg=("views", "mean")).reset_index()
                pivot = pivot.merge(bl_metrics, left_on=["techs", "date"], right_on=["techs", "date"], how="left")
            else:
                pivot["blog_posts"] = 0
                pivot["blog_views_avg"] = 0
        except Exception:
            logger.exception("Failed computing blog metrics")
            pivot["blog_posts"] = 0
            pivot["blog_views_avg"] = 0

        # fill missing numeric columns
        pivot = pivot.sort_values(["techs", "date"])
        numeric_cols = [c for c in pivot.columns if c not in ("techs", "date")]
        for c in numeric_cols:
            if pivot[c].dtype == object:
                try:
                    pivot[c] = pd.to_numeric(pivot[c], errors="coerce")
                except Exception:
                    pass
        pivot = pivot.fillna(0)

        # compute rolling features per tech
        features_rows = []
        for tech, g in pivot.groupby("techs"):
            g = g.sort_values("date").set_index(pd.to_datetime(g["date"]))
            # ensure the index has a stable name so reset_index doesn't try to
            # insert a column with the same name as an existing column (e.g. 'date')
            g.index.name = "timestamp"
            # ensure expected columns exist
            for base_col in ["mentions", "github_authors"] + source_cols:
                if base_col not in g.columns:
                    g[base_col] = 0

            for w in window_days_list:
                g[f"mentions_{w}d_mean"] = g["mentions"].rolling(w, min_periods=1).mean()
                g[f"mentions_{w}d_sum"] = g["mentions"].rolling(w, min_periods=1).sum()
                # job_postings rolling
                if "job_postings" in g.columns:
                    g[f"job_postings_{w}d_sum"] = g["job_postings"].rolling(w, min_periods=1).sum()
                if "github_events" in g.columns or "github" in g.columns:
                    g[f"github_events_{w}d_sum"] = g.get("github_events", g.get("github", 0)).rolling(w, min_periods=1).sum()
                g[f"github_authors_{w}d_sum"] = g.get("contributors_n", 0).rolling(w, min_periods=1).sum()

            # previous windows
            g["mentions_7d_prev"] = g["mentions_7d_mean"].shift(7)
            g["mentions_30d_prev"] = g["mentions_30d_mean"].shift(30) if "mentions_30d_mean" in g.columns else g["mentions_7d_mean"].shift(30)

            # velocity and growth
            g["mentions_velocity"] = g["mentions_7d_mean"] - g["mentions_30d_mean"] if "mentions_30d_mean" in g.columns else g["mentions_7d_mean"]
            g["mentions_growth_pct"] = (g["mentions_7d_mean"] / g["mentions_7d_prev"].replace({0: np.nan}) - 1).fillna(0)

            # twitter engagement velocity
            if "engagement_sum" in g.columns:
                g["engagement_7d_mean"] = g["engagement_sum"].rolling(7, min_periods=1).mean()
                g["engagement_velocity"] = g["engagement_7d_mean"].diff().fillna(0)

            # salary growth
            if "avg_salary" in g.columns:
                g["salary_7d_mean"] = g["avg_salary"].rolling(7, min_periods=1).mean()
                g["salary_growth_pct"] = (g["salary_7d_mean"].pct_change().fillna(0))

            # trend value fill
            if "trend_score_avg" not in g.columns:
                g["trend_score_avg"] = 0

            # spike detection: z-score on mentions over 7-day window
            try:
                g["mentions_7d_std"] = g["mentions"].rolling(7, min_periods=1).std().fillna(0)
                g["mentions_spike"] = ((g["mentions"] - g["mentions_7d_mean"]) / (g["mentions_7d_std"].replace({0: 1}))).fillna(0) > 3
            except Exception:
                g["mentions_spike"] = False

            # popularity score: combine weighted signals
            g["technology_popularity_score"] = (
                0.5 * g["mentions_7d_mean"].fillna(0)
                + 0.2 * g["trend_score_avg"].fillna(0)
                + 0.2 * g.get("github_authors_7d_sum", 0).fillna(0)
                + 0.1 * g.get("job_postings_7d_sum", 0).fillna(0)
            )

            # ecosystem momentum
            g["ecosystem_momentum_score"] = (
                g["mentions_velocity"].fillna(0)
                + g.get("engagement_velocity", 0).fillna(0)
                + g.get("github_events_7d_sum", 0).fillna(0)
            )

            out = g.reset_index()
            out["tech"] = tech
            features_rows.append(out)

        if not features_rows:
            logger.info("No features computed")
            return

        feat_df = pd.concat(features_rows, ignore_index=True)
        feat_df["date"] = pd.to_datetime(feat_df["timestamp"]).dt.date

        # write per-tech per-date parquet files
        base = Path(self.feature_dir) / "features"
        for tech, g in feat_df.groupby("tech"):
            tech_dir = base / tech
            tech_dir.mkdir(parents=True, exist_ok=True)
            for _, row in g.iterrows():
                date_str = pd.to_datetime(row["date"]).date().isoformat()
                out_path = tech_dir / f"{date_str}.parquet"
                row_dict = row.drop(labels=["tech"]).to_dict()
                # keep only JSON-serializable / numeric keys
                try:
                    pd.DataFrame([row_dict]).to_parquet(out_path, index=False, engine="pyarrow")
                except Exception:
                    logger.exception("Failed to write feature file %s", out_path)

        logger.info("Feature generation complete: %d techs", feat_df["tech"].nunique())


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", nargs="*", type=int, default=None)
    args = parser.parse_args()
    FeatureEngineer().generate_daily_features(window_days_list=args.windows)
