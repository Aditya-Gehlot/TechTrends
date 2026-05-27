"""Feature engineering for the local generated TechTrends corpus.

The engineer reads normalized records from ``processed/``, computes daily
per-technology aggregates, adds rolling windows, and writes:

- ``feature_store/features_all.parquet`` for ML/API/dashboard reads
- ``feature_store/features/<safe-tech>/latest.parquet`` for lightweight lookup
- optional daily feature partitions when ``FEATURE_WRITE_DAILY_PARTITIONS=true``
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterable, List
from urllib.parse import quote

import numpy as np
import pandas as pd

from config import settings

logger = logging.getLogger(__name__)

try:
    from db import repositories as db_repo
except Exception:  # pragma: no cover - DB support is optional at runtime
    db_repo = None


class FeatureEngineer:
    def __init__(self, processed_dir: Path | None = None, feature_dir: Path | None = None):
        self.processed_dir = Path(processed_dir or settings.PROCESSED_DIR)
        self.feature_dir = Path(feature_dir or settings.FEATURE_STORE_DIR)

    def _load_processed(self, sources: Iterable[str] | None = None) -> pd.DataFrame:
        parts = []
        base = self.processed_dir
        source_filter = set(sources or [])
        if not base.exists():
            return pd.DataFrame()

        for source_dir in base.iterdir():
            if not source_dir.is_dir() or source_dir.name.startswith("_"):
                continue
            if source_filter and source_dir.name not in source_filter:
                continue
            for file_path in source_dir.rglob("*.parquet"):
                try:
                    df = pd.read_parquet(file_path)
                except Exception:
                    logger.exception("Failed to read processed parquet %s", file_path)
                    continue
                required = {"source", "id", "timestamp", "techs", "raw"}
                if not required.issubset(df.columns):
                    logger.warning("Skipping %s because it is missing normalized columns", file_path)
                    continue
                parts.append(df)

        if not parts:
            return pd.DataFrame()

        df = pd.concat(parts, ignore_index=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])
        df["techs"] = df["techs"].apply(self._as_list)
        return df

    def _as_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        try:
            if pd.isna(value):
                return []
        except Exception:
            pass
        if isinstance(value, np.ndarray):
            value = value.tolist()
        if isinstance(value, (list, tuple, set)):
            return [str(v).strip() for v in value if str(v).strip()]
        text = str(value).strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                loaded = json.loads(text)
                if isinstance(loaded, list):
                    return [str(v).strip() for v in loaded if str(v).strip()]
            except Exception:
                pass
        delimiter = "|" if "|" in text and "," not in text else ","
        return [part.strip() for part in text.split(delimiter) if part.strip()]

    def _safe_get(self, value: Any, *keys: str, default: Any = None) -> Any:
        try:
            current = value
            if isinstance(current, str) and current.startswith("{"):
                current = json.loads(current)
            for key in keys:
                if isinstance(current, dict):
                    current = current.get(key)
                else:
                    return default
            return default if current is None else current
        except Exception:
            return default

    def _num(self, value: Any, *keys: str, default: float = 0.0) -> float:
        raw = self._safe_get(value, *keys, default=default) if keys else value
        try:
            if raw is None or pd.isna(raw):
                return default
        except Exception:
            pass
        if isinstance(raw, str):
            text = raw.strip().lower()
            if text in {"true", "yes"}:
                return 1.0
            if text in {"false", "no"}:
                return 0.0
        try:
            return float(raw)
        except Exception:
            return default

    def _risk_value(self, value: Any) -> str:
        risk = self._safe_get(value, "risk_indicator", default="")
        return str(risk or "").strip().lower()

    def _safe_tech_dir(self, tech: str) -> str:
        return quote(str(tech), safe="")

    def _series(self, df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
        if column in df.columns:
            return pd.to_numeric(df[column], errors="coerce").fillna(default)
        return pd.Series(default, index=df.index, dtype="float64")

    def _merge_metric(self, pivot: pd.DataFrame, metric_df: pd.DataFrame) -> pd.DataFrame:
        if metric_df.empty:
            return pivot
        return pivot.merge(metric_df, on=["techs", "date"], how="left")

    def generate_daily_features(
        self,
        window_days_list: List[int] | None = None,
        sources: Iterable[str] | None = None,
        write_partitions: bool | None = None,
        run_id: str | None = None,
    ) -> pd.DataFrame:
        window_days_list = window_days_list or [7, 30]
        write_partitions = settings.FEATURE_WRITE_DAILY_PARTITIONS if write_partitions is None else write_partitions

        df = self._load_processed(sources=sources)
        if df.empty:
            logger.info("No processed data found to generate features")
            return pd.DataFrame()

        df = df.explode("techs")
        df = df[~df["techs"].isnull()].copy()
        df["techs"] = df["techs"].astype(str).str.strip()
        df = df[df["techs"] != ""]
        df["date"] = df["timestamp"].dt.date
        df = df.drop_duplicates(subset=["source", "id", "techs", "date"])

        counts = df.groupby(["techs", "date", "source"]).agg(count=("id", "count")).reset_index()
        pivot = counts.pivot_table(index=["techs", "date"], columns="source", values="count", fill_value=0).reset_index()
        pivot.columns.name = None
        source_cols = [c for c in pivot.columns if c not in {"techs", "date"}]
        pivot["mentions"] = pivot[source_cols].sum(axis=1) if source_cols else 0

        raw = df["raw"]
        df["_trend_score"] = raw.apply(lambda r: self._num(r, "trend_score", default=np.nan))
        df["_sentiment_score"] = raw.apply(lambda r: self._num(r, "sentiment_score", default=np.nan))
        df["_innovation_score"] = raw.apply(lambda r: self._num(r, "innovation_score", default=np.nan))
        df["_adoption_score"] = raw.apply(lambda r: self._num(r, "adoption_score", default=np.nan))
        df["_popularity_growth_pct"] = raw.apply(lambda r: self._num(r, "popularity_growth_pct", default=np.nan))
        df["_volatility_metric"] = raw.apply(lambda r: self._num(r, "volatility_metric", default=np.nan))
        df["_company"] = raw.apply(lambda r: self._safe_get(r, "company", default=None))
        df["_country"] = raw.apply(lambda r: self._safe_get(r, "country", default=None))
        df["_risk"] = raw.apply(self._risk_value)

        generic = (
            df.groupby(["techs", "date"])
            .agg(
                signal_trend_score_avg=("_trend_score", "mean"),
                sentiment_score_avg=("_sentiment_score", "mean"),
                innovation_score_avg=("_innovation_score", "mean"),
                adoption_score_avg=("_adoption_score", "mean"),
                popularity_growth_signal_avg=("_popularity_growth_pct", "mean"),
                volatility_metric_avg=("_volatility_metric", "mean"),
                company_count=("_company", lambda s: s.dropna().nunique()),
                country_count=("_country", lambda s: s.dropna().nunique()),
                high_risk_records=("_risk", lambda s: int((s == "high").sum())),
                moderate_risk_records=("_risk", lambda s: int((s == "moderate").sum())),
            )
            .reset_index()
        )
        pivot = self._merge_metric(pivot, generic)

        # Hiring metrics.
        ln = df[df["source"].isin(["linkedin_jobs", "linkedin"])].copy()
        if not ln.empty:
            ln["_salary"] = ln["raw"].apply(lambda r: self._num(r, "salary_usd", default=np.nan))
            ln["_role"] = ln["raw"].apply(lambda r: self._safe_get(r, "role", default=None))
            ln["_skills"] = ln["raw"].apply(lambda r: self._as_list(self._safe_get(r, "skills", default=[])))
            ln["_hiring_index"] = ln["raw"].apply(lambda r: self._num(r, "hiring_index", default=np.nan))
            ln["_funding_signal"] = ln["raw"].apply(lambda r: self._num(r, "funding_signal", default=np.nan))
            skill_counts = (
                ln.explode("_skills")
                .dropna(subset=["_skills"])
                .groupby(["techs", "date"])
                .agg(skill_count=("_skills", "count"))
                .reset_index()
            )
            ln_metrics = (
                ln.groupby(["techs", "date"])
                .agg(
                    job_postings=("id", "count"),
                    avg_salary=("_salary", "mean"),
                    unique_roles=("_role", lambda s: s.dropna().nunique()),
                    hiring_index_avg=("_hiring_index", "mean"),
                    funding_signal_avg=("_funding_signal", "mean"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(self._merge_metric(pivot, ln_metrics), skill_counts)

        # Twitter/X metrics.
        tw = df[df["source"].isin(["twitter_stream", "twitter"])].copy()
        if not tw.empty:
            def sentiment(row: Any) -> float:
                numeric = self._num(row, "sentiment_score", default=np.nan)
                if not np.isnan(numeric):
                    return numeric
                label = str(self._safe_get(row, "sentiment", default="")).lower()
                if "pos" in label:
                    return 1.0
                if "neg" in label:
                    return -1.0
                return 0.0

            tw["_sentiment"] = tw["raw"].apply(sentiment)
            tw["_engagement"] = tw["raw"].apply(
                lambda r: self._num(r, "likes") + self._num(r, "retweets")
            )
            tw_metrics = (
                tw.groupby(["techs", "date"])
                .agg(
                    twitter_count=("id", "count"),
                    twitter_sentiment_avg=("_sentiment", "mean"),
                    twitter_engagement_sum=("_engagement", "sum"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, tw_metrics)

        # GitHub metrics.
        gh = df[df["source"].isin(["github_events", "github", settings.GITHUB_TOPIC])].copy()
        if not gh.empty:
            gh["_stars"] = gh["raw"].apply(lambda r: self._num(r, "stars_added"))
            gh["_forks"] = gh["raw"].apply(lambda r: self._num(r, "forks_added"))
            gh["_contributors"] = gh["raw"].apply(lambda r: self._num(r, "contributors"))
            gh["_watchers"] = gh["raw"].apply(lambda r: self._num(r, "watchers_added"))
            gh["_issues"] = gh["raw"].apply(lambda r: self._num(r, "issue_count"))
            gh["_release"] = gh["raw"].apply(lambda r: self._num(r, "release_flag"))
            gh_metrics = (
                gh.groupby(["techs", "date"])
                .agg(
                    github_event_count=("id", "count"),
                    stars_sum=("_stars", "sum"),
                    forks_sum=("_forks", "sum"),
                    contributors_n=("_contributors", "sum"),
                    watchers_sum=("_watchers", "sum"),
                    issue_count_sum=("_issues", "sum"),
                    release_count=("_release", "sum"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, gh_metrics)

        # StackOverflow metrics.
        so = df[df["source"].isin(["stackoverflow_questions", "stackoverflow", settings.STACKOVERFLOW_TOPIC])].copy()
        if not so.empty:
            so["_answers"] = so["raw"].apply(lambda r: self._num(r, "answers"))
            so["_views"] = so["raw"].apply(lambda r: self._num(r, "views"))
            so["_score"] = so["raw"].apply(lambda r: self._num(r, "score"))
            so["_accepted"] = so["raw"].apply(lambda r: self._num(r, "accepted_answer"))
            so_metrics = (
                so.groupby(["techs", "date"])
                .agg(
                    so_questions=("id", "count"),
                    avg_answers=("_answers", "mean"),
                    accepted_rate=("_accepted", "mean"),
                    so_views_sum=("_views", "sum"),
                    so_score_sum=("_score", "sum"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, so_metrics)

        # Google Trends metrics.
        gt = df[df["source"].isin(["google_trends", settings.GOOGLE_TRENDS_TOPIC])].copy()
        if not gt.empty:
            gt["_trend_score"] = gt["raw"].apply(lambda r: self._num(r, "trend_score"))
            gt_metrics = (
                gt.groupby(["techs", "date"])
                .agg(google_trend_score_avg=("_trend_score", "mean"))
                .reset_index()
            )
            pivot = self._merge_metric(pivot, gt_metrics)

        # Blogs and long-form content metrics.
        bl = df[df["source"].isin(["tech_blogs", "blogs", settings.BLOG_TOPIC])].copy()
        if not bl.empty:
            bl["_views"] = bl["raw"].apply(lambda r: self._num(r, "views"))
            bl["_read_time"] = bl["raw"].apply(lambda r: self._num(r, "reading_time_minutes"))
            bl["_hiring"] = bl["raw"].apply(lambda r: self._num(r, "hiring_activity_index", default=np.nan))
            bl_metrics = (
                bl.groupby(["techs", "date"])
                .agg(
                    blog_posts=("id", "count"),
                    blog_views_sum=("_views", "sum"),
                    blog_reading_time_avg=("_read_time", "mean"),
                    blog_hiring_activity_avg=("_hiring", "mean"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, bl_metrics)

        # Community/social corpus: Reddit and Hacker News.
        community = df[df["source"].isin(["reddit_discussions", "hackernews_posts"])].copy()
        if not community.empty:
            community["_upvotes"] = community["raw"].apply(
                lambda r: self._num(r, "upvotes") + self._num(r, "points")
            )
            community["_comments"] = community["raw"].apply(lambda r: self._num(r, "comments"))
            community["_engagement"] = community["_upvotes"] + community["_comments"]
            community_metrics = (
                community.groupby(["techs", "date"])
                .agg(
                    community_posts=("id", "count"),
                    community_engagement_sum=("_engagement", "sum"),
                    community_comments_sum=("_comments", "sum"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, community_metrics)

        # Video, launches, news, Kaggle, funding, and market-event signals.
        yt = df[df["source"].isin(["youtube_ai_content"])].copy()
        if not yt.empty:
            yt["_views"] = yt["raw"].apply(lambda r: self._num(r, "views"))
            yt["_likes"] = yt["raw"].apply(lambda r: self._num(r, "likes"))
            yt["_comments"] = yt["raw"].apply(lambda r: self._num(r, "comments"))
            yt["_watch"] = yt["raw"].apply(lambda r: self._num(r, "watch_time_minutes"))
            yt_metrics = (
                yt.groupby(["techs", "date"])
                .agg(
                    youtube_videos=("id", "count"),
                    youtube_views_sum=("_views", "sum"),
                    youtube_likes_sum=("_likes", "sum"),
                    youtube_comments_sum=("_comments", "sum"),
                    youtube_watch_time_sum=("_watch", "sum"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, yt_metrics)

        ph = df[df["source"].isin(["producthunt_launches"])].copy()
        if not ph.empty:
            ph["_upvotes"] = ph["raw"].apply(lambda r: self._num(r, "upvotes"))
            ph["_comments"] = ph["raw"].apply(lambda r: self._num(r, "comments"))
            ph_metrics = (
                ph.groupby(["techs", "date"])
                .agg(
                    producthunt_launch_count=("id", "count"),
                    producthunt_upvotes_sum=("_upvotes", "sum"),
                    producthunt_comments_sum=("_comments", "sum"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, ph_metrics)

        news = df[df["source"].isin(["news_media_mentions"])].copy()
        if not news.empty:
            news["_mentions"] = news["raw"].apply(lambda r: self._num(r, "mention_count"))
            news["_funding"] = news["raw"].apply(lambda r: self._num(r, "funding_estimate_musd"))
            news["_hiring"] = news["raw"].apply(lambda r: self._num(r, "hiring_activity_index"))
            news_metrics = (
                news.groupby(["techs", "date"])
                .agg(
                    news_articles=("id", "count"),
                    news_mention_count_sum=("_mentions", "sum"),
                    media_funding_estimate_musd=("_funding", "sum"),
                    media_hiring_activity_avg=("_hiring", "mean"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, news_metrics)

        kaggle = df[df["source"].isin(["kaggle_ml_activity"])].copy()
        if not kaggle.empty:
            kaggle["_kernels"] = kaggle["raw"].apply(lambda r: self._num(r, "kernels_created"))
            kaggle["_votes"] = kaggle["raw"].apply(lambda r: self._num(r, "notebook_votes"))
            kaggle["_downloads"] = kaggle["raw"].apply(lambda r: self._num(r, "dataset_downloads"))
            kaggle["_medal_rate"] = kaggle["raw"].apply(lambda r: self._num(r, "medal_rate", default=np.nan))
            kaggle_metrics = (
                kaggle.groupby(["techs", "date"])
                .agg(
                    kaggle_activities=("id", "count"),
                    kaggle_kernels_sum=("_kernels", "sum"),
                    kaggle_votes_sum=("_votes", "sum"),
                    kaggle_downloads_sum=("_downloads", "sum"),
                    kaggle_medal_rate_avg=("_medal_rate", "mean"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, kaggle_metrics)

        funding = df[df["source"].isin(["startup_funding"])].copy()
        if not funding.empty:
            funding["_amount"] = funding["raw"].apply(lambda r: self._num(r, "amount_musd"))
            funding["_valuation"] = funding["raw"].apply(lambda r: self._num(r, "valuation_musd", default=np.nan))
            funding["_hiring_impact"] = funding["raw"].apply(
                lambda r: self._num(r, "estimated_hiring_impact_pct", default=np.nan)
            )
            funding_metrics = (
                funding.groupby(["techs", "date"])
                .agg(
                    funding_events=("id", "count"),
                    funding_amount_musd=("_amount", "sum"),
                    valuation_musd_avg=("_valuation", "mean"),
                    estimated_hiring_impact_avg=("_hiring_impact", "mean"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, funding_metrics)

        events = df[df["source"].isin(["market_events"])].copy()
        if not events.empty:
            events["_impact"] = events["raw"].apply(lambda r: self._num(r, "impact_score"))
            events["_sentiment_shift"] = events["raw"].apply(lambda r: self._num(r, "sentiment_shift", default=np.nan))
            event_metrics = (
                events.groupby(["techs", "date"])
                .agg(
                    market_event_count=("id", "count"),
                    market_event_impact_sum=("_impact", "sum"),
                    market_event_sentiment_shift_avg=("_sentiment_shift", "mean"),
                )
                .reset_index()
            )
            pivot = self._merge_metric(pivot, event_metrics)

        pivot = pivot.sort_values(["techs", "date"])
        numeric_cols = [c for c in pivot.columns if c not in {"techs", "date"}]
        for col in numeric_cols:
            pivot[col] = pd.to_numeric(pivot[col], errors="coerce")
        pivot = pivot.fillna(0)
        if "google_trend_score_avg" in pivot.columns:
            pivot["trend_score_avg"] = pivot["google_trend_score_avg"].where(
                pivot["google_trend_score_avg"] != 0,
                pivot.get("signal_trend_score_avg", 0),
            )
        elif "signal_trend_score_avg" in pivot.columns:
            pivot["trend_score_avg"] = pivot["signal_trend_score_avg"]
        else:
            pivot["trend_score_avg"] = 0.0

        features_rows = []
        for tech, group in pivot.groupby("techs"):
            ordered = group.sort_values("date").copy()
            g = ordered.set_index(pd.to_datetime(ordered["date"]))
            g.index.name = "timestamp"

            for base_col in ["mentions", *source_cols]:
                if base_col not in g.columns:
                    g[base_col] = 0.0

            for window in window_days_list:
                g[f"mentions_{window}d_mean"] = self._series(g, "mentions").rolling(window, min_periods=1).mean()
                g[f"mentions_{window}d_sum"] = self._series(g, "mentions").rolling(window, min_periods=1).sum()
                g[f"job_postings_{window}d_sum"] = self._series(g, "job_postings").rolling(window, min_periods=1).sum()
                g[f"github_events_{window}d_sum"] = self._series(g, "github_events").rolling(window, min_periods=1).sum()
                g[f"github_authors_{window}d_sum"] = self._series(g, "contributors_n").rolling(window, min_periods=1).sum()
                g[f"community_engagement_{window}d_sum"] = self._series(g, "community_engagement_sum").rolling(window, min_periods=1).sum()
                g[f"youtube_views_{window}d_sum"] = self._series(g, "youtube_views_sum").rolling(window, min_periods=1).sum()
                g[f"funding_amount_{window}d_sum"] = self._series(g, "funding_amount_musd").rolling(window, min_periods=1).sum()
                g[f"kaggle_activity_{window}d_sum"] = (
                    self._series(g, "kaggle_kernels_sum")
                    + self._series(g, "kaggle_votes_sum")
                    + self._series(g, "kaggle_downloads_sum")
                ).rolling(window, min_periods=1).sum()
                g[f"market_event_impact_{window}d_sum"] = (
                    self._series(g, "market_event_impact_sum").rolling(window, min_periods=1).sum()
                )

            g["mentions_7d_prev"] = g["mentions_7d_mean"].shift(7)
            g["mentions_30d_prev"] = g["mentions_30d_mean"].shift(30) if "mentions_30d_mean" in g.columns else 0
            g["mentions_velocity"] = g["mentions_7d_mean"] - self._series(g, "mentions_30d_mean")
            g["mentions_growth_pct"] = (
                g["mentions_7d_mean"] / g["mentions_7d_prev"].replace({0: np.nan}) - 1
            ).replace([np.inf, -np.inf], 0).fillna(0)

            g["engagement_7d_sum"] = (
                self._series(g, "twitter_engagement_sum")
                + self._series(g, "community_engagement_sum")
                + self._series(g, "youtube_likes_sum")
                + self._series(g, "producthunt_upvotes_sum")
                + self._series(g, "so_score_sum")
            ).rolling(7, min_periods=1).sum()
            g["engagement_velocity"] = g["engagement_7d_sum"].diff().fillna(0)

            g["salary_7d_mean"] = self._series(g, "avg_salary").rolling(7, min_periods=1).mean()
            g["salary_growth_pct"] = g["salary_7d_mean"].pct_change().replace([np.inf, -np.inf], 0).fillna(0)

            g["mentions_7d_std"] = self._series(g, "mentions").rolling(7, min_periods=1).std().fillna(0)
            g["mentions_spike"] = (
                (self._series(g, "mentions") - g["mentions_7d_mean"]) / g["mentions_7d_std"].replace({0: 1})
            ).fillna(0) > 3

            engagement_component = np.log1p(g["engagement_7d_sum"].clip(lower=0))
            video_component = np.log1p(self._series(g, "youtube_views_7d_sum").clip(lower=0))
            funding_component = np.log1p(self._series(g, "funding_amount_30d_sum").clip(lower=0))
            kaggle_component = np.log1p(self._series(g, "kaggle_activity_7d_sum").clip(lower=0))
            trend_component = self._series(g, "trend_score_avg")

            g["technology_popularity_score"] = (
                0.30 * g["mentions_7d_mean"].fillna(0)
                + 0.20 * trend_component.fillna(0)
                + 0.12 * engagement_component.fillna(0)
                + 0.10 * self._series(g, "github_events_7d_sum")
                + 0.08 * self._series(g, "job_postings_7d_sum")
                + 0.06 * video_component.fillna(0)
                + 0.05 * funding_component.fillna(0)
                + 0.04 * kaggle_component.fillna(0)
                + 0.03 * self._series(g, "market_event_impact_7d_sum")
                + 0.02 * self._series(g, "adoption_score_avg")
            )

            g["ecosystem_momentum_score"] = (
                g["mentions_velocity"].fillna(0)
                + 0.05 * g["engagement_velocity"].fillna(0)
                + self._series(g, "github_events_7d_sum")
                + 0.5 * self._series(g, "market_event_impact_7d_sum")
                + self._series(g, "popularity_growth_signal_avg")
            )

            out = g.reset_index()
            out["tech"] = tech
            features_rows.append(out)

        if not features_rows:
            logger.info("No features computed")
            return pd.DataFrame()

        feat_df = pd.concat(features_rows, ignore_index=True)
        feat_df["date"] = pd.to_datetime(feat_df["timestamp"]).dt.date

        consolidated_path = Path(self.feature_dir) / "features_all.parquet"
        consolidated_path.parent.mkdir(parents=True, exist_ok=True)
        feat_df.to_parquet(consolidated_path, index=False, engine="pyarrow")
        logger.info(
            "Wrote consolidated feature dataset rows=%d techs=%d path=%s",
            len(feat_df),
            feat_df["tech"].nunique(),
            consolidated_path,
        )

        self._write_feature_lookup(feat_df, write_partitions=write_partitions)
        if db_repo is not None:
            db_repo.insert_daily_features_batch(feat_df, external_run_id=run_id)
            db_repo.create_feature_snapshot(
                feat_df,
                artifact_path=str(consolidated_path),
                feature_index_path=str(Path(self.feature_dir) / "feature_index.json"),
                external_run_id=run_id,
            )
        return feat_df

    def _write_feature_lookup(self, feat_df: pd.DataFrame, write_partitions: bool) -> None:
        base = Path(self.feature_dir) / "features"
        base.mkdir(parents=True, exist_ok=True)

        feature_index: dict[str, str] = {}
        grouped = feat_df.sort_values("timestamp").groupby("tech", sort=False)
        for tech, group in grouped:
            slug = self._safe_tech_dir(str(tech))
            feature_index[slug] = str(tech)
            tech_dir = base / slug
            tech_dir.mkdir(parents=True, exist_ok=True)

            latest = group.tail(1)
            latest.to_parquet(tech_dir / "latest.parquet", index=False, engine="pyarrow")

            if write_partitions:
                for _, row in group.iterrows():
                    date_str = pd.to_datetime(row["date"]).date().isoformat()
                    pd.DataFrame([row.to_dict()]).to_parquet(tech_dir / f"{date_str}.parquet", index=False, engine="pyarrow")

        (Path(self.feature_dir) / "feature_index.json").write_text(json.dumps(feature_index, indent=2), encoding="utf-8")
        mode = "daily partitions" if write_partitions else "latest partitions"
        logger.info("Feature lookup write complete using %s for %d techs", mode, len(feature_index))


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", nargs="*", type=int, default=None)
    parser.add_argument("--sources", nargs="*", default=None)
    parser.add_argument("--write-daily-partitions", action="store_true")
    args = parser.parse_args()
    FeatureEngineer().generate_daily_features(
        window_days_list=args.windows,
        sources=args.sources,
        write_partitions=args.write_daily_partitions or None,
    )
