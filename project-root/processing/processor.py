"""S3 -> Parquet processing pipeline.

Reads raw JSONL objects from S3/MinIO, normalizes records per-source,
deduplicates and writes analytics-friendly Parquet files partitioned by
source/year/month/day under the processed directory.

Features:
- resilient JSONL parsing with malformed-line handling
- checkpointing of processed S3 keys for idempotency
- per-file and per-record deduplication (within-file)
- configurable prefix and run-once / batch modes
"""
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List

import botocore
import boto3
import pandas as pd

from config import settings
from .schemas import RawRecord, NormalizedRecord

logger = logging.getLogger(__name__)


def _extract_techs(text: str, keywords: List[str]) -> List[str]:
    if not text:
        return []
    text_l = text.lower()
    found = []
    for kw in keywords:
        if not kw:
            continue
        if kw.lower() in text_l:
            found.append(kw)
    return sorted(set(found))


class S3Processor:
    CHECKPOINT_FILE = settings.STATE_DIR / "processing_checkpoints.json"

    def __init__(self, bucket: str = None, prefix: str = None):
        if bucket is None:
            bucket = settings.RAW_S3_BUCKET
        if not bucket:
            raise ValueError("RAW_S3_BUCKET must be set to run the processor")
        self.bucket = bucket
        self.prefix = (prefix or settings.RAW_S3_PREFIX or "raw").strip("/")
        self.s3 = boto3.client(
            "s3",
            region_name=settings.RAW_S3_REGION,
            endpoint_url=settings.RAW_S3_ENDPOINT_URL,
            aws_access_key_id=settings.RAW_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.RAW_S3_SECRET_ACCESS_KEY,
        )
        self.keywords = getattr(settings, "PYTRENDS_KEYWORDS", [])
        self._checkpoints = self._load_checkpoints()

    def _load_checkpoints(self) -> Dict[str, Dict]:
        try:
            if self.CHECKPOINT_FILE.exists():
                return json.loads(self.CHECKPOINT_FILE.read_text())
        except Exception:
            logger.exception("Failed to load processing checkpoints")
        return {}

    def _save_checkpoints(self):
        try:
            tmp = self.CHECKPOINT_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._checkpoints))
            tmp.replace(self.CHECKPOINT_FILE)
        except Exception:
            logger.exception("Failed to write processing checkpoints")

    def list_objects(self, prefix: str = None):
        p = f"{(prefix or self.prefix).strip('/')}/"
        paginator = self.s3.get_paginator("list_objects_v2")
        try:
            for page in paginator.paginate(Bucket=self.bucket, Prefix=p):
                for obj in page.get("Contents", []):
                    yield obj["Key"]
        except botocore.exceptions.ClientError:
            logger.exception("Error listing objects with prefix=%s", p)

    def _read_object_lines(self, key: str):
        # resilient read with a simple retry
        for attempt in range(3):
            try:
                obj = self.s3.get_object(Bucket=self.bucket, Key=key)
                body = obj["Body"].read().decode("utf-8")
                for line in body.splitlines():
                    if line.strip():
                        yield line
                return
            except botocore.exceptions.ClientError:
                logger.exception("Failed to read s3://%s/%s (attempt=%d)", self.bucket, key, attempt + 1)
                time.sleep(1 + attempt)
            except Exception:
                logger.exception("Unexpected error reading s3://%s/%s", self.bucket, key)
                return

    def _infer_topic_from_key(self, key: str) -> str:
        # key expected format: <prefix>/<topic>/... -> try to extract topic
        parts = key.split("/")
        prefix_parts = self.prefix.split("/") if self.prefix else []
        # find first part after prefix
        for i, part in enumerate(parts):
            if prefix_parts and i < len(prefix_parts) and part == prefix_parts[i]:
                continue
            # the next part is likely the topic
            return part
        return parts[0] if parts else "unknown"

    def normalize(self, raw: RawRecord) -> NormalizedRecord | None:
        topic = raw.topic
        payload = raw.payload or {}

        # default timestamp
        ts = None
        if raw.ingested_at:
            ts = raw.ingested_at
        elif raw.timestamp:
            try:
                ts = datetime.fromtimestamp(int(raw.timestamp) / 1000.0, tz=timezone.utc)
            except Exception:
                ts = None

        if topic == settings.GITHUB_TOPIC or topic == "github_events" or topic == "github":
            pid = str(payload.get("id") or payload.get("event") or payload.get("node_id") or "")
            created = payload.get("created_at") or payload.get("created") or payload.get("created_at")
            if created and not ts:
                try:
                    ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except Exception:
                    ts = None
            repo = None
            try:
                repo = payload.get("repo", {}).get("name") if isinstance(payload.get("repo"), dict) else payload.get("repo")
            except Exception:
                repo = None
            text = " ".join(filter(None, [repo, payload.get("type", ""), json.dumps(payload.get("payload", {}))]))
            techs = _extract_techs(text, self.keywords)
            return NormalizedRecord(
                source="github",
                id=pid or f"github:{raw.offset}",
                timestamp=ts or datetime.now(timezone.utc),
                title=None,
                text=text,
                tags=[],
                url=None,
                techs=techs,
                raw=payload,
            )

        if topic == settings.STACKOVERFLOW_TOPIC or topic == "stackoverflow":
            qid = str(payload.get("question_id") or payload.get("id") or "")
            created = payload.get("creation_date")
            if created and not ts:
                try:
                    ts = datetime.utcfromtimestamp(int(created))
                except Exception:
                    ts = None
            title = payload.get("title")
            tags = payload.get("tags") or []
            text = " ".join(filter(None, [title, " ".join(tags), payload.get("link") or ""]))
            techs = _extract_techs(" ".join([title or "", " ".join(tags) if tags else ""]), self.keywords)
            return NormalizedRecord(
                source="stackoverflow",
                id=qid or f"stackoverflow:{raw.offset}",
                timestamp=ts or datetime.now(timezone.utc),
                title=title,
                text=text,
                tags=tags,
                url=payload.get("link"),
                techs=techs,
                raw=payload,
            )

        if topic == settings.BLOG_TOPIC or topic == "tech_blogs" or topic == "blogs":
            bid = str(payload.get("id") or payload.get("link") or "")
            pub = payload.get("published")
            if pub and not ts:
                try:
                    ts = datetime.fromisoformat(pub)
                except Exception:
                    ts = None
            title = payload.get("title")
            summary = payload.get("summary")
            text = " ".join(filter(None, [title, summary]))
            techs = _extract_techs(text, self.keywords)
            return NormalizedRecord(
                source="blogs",
                id=bid or f"blogs:{raw.offset}",
                timestamp=ts or datetime.now(timezone.utc),
                title=title,
                text=text,
                tags=[],
                url=payload.get("link"),
                techs=techs,
                raw=payload,
            )

        if topic == settings.GOOGLE_TRENDS_TOPIC or topic == "google_trends":
            gid = str(payload.get("timestamp") or payload.get("ts") or "")
            try:
                ts = datetime.fromisoformat(payload.get("timestamp")) if isinstance(payload.get("timestamp"), str) else ts
            except Exception:
                pass
            vals = payload.get("values") or []
            text = " ".join([v.get("term", "") for v in vals])
            techs = [v.get("term") for v in vals if v.get("term")]
            return NormalizedRecord(
                source="google_trends",
                id=gid or f"google:{raw.offset}",
                timestamp=ts or datetime.now(timezone.utc),
                title=None,
                text=text,
                tags=[],
                url=None,
                techs=techs,
                raw=payload,
            )

        # generic fallback
        try:
            pid = str(payload.get("id") or payload.get("key") or f"{topic}:{raw.offset}")
        except Exception:
            pid = f"{topic}:{raw.offset}"
        text = json.dumps(payload)
        techs = _extract_techs(text, self.keywords)
        return NormalizedRecord(
            source=topic,
            id=pid,
            timestamp=ts or datetime.now(timezone.utc),
            title=None,
            text=text,
            tags=[],
            url=None,
            techs=techs,
            raw=payload,
        )

    def process_key(self, key: str):
        # skip if already processed
        if key in self._checkpoints:
            logger.info("Skipping already-processed s3://%s/%s", self.bucket, key)
            return 0

        rows = []
        seen_ids = set()
        malformed = 0
        parsed = 0
        for line in self._read_object_lines(key):
            try:
                obj = json.loads(line)
            except Exception:
                logger.exception("Skipping malformed JSON line in %s", key)
                malformed += 1
                continue
            parsed += 1
            # infer raw record shape
            try:
                raw = RawRecord.parse_obj(obj)
            except Exception:
                # try to infer topic from key if missing
                try:
                    topic = obj.get("topic") or self._infer_topic_from_key(key)
                    raw = RawRecord(
                        topic=topic,
                        partition=obj.get("partition"),
                        offset=obj.get("offset"),
                        timestamp=obj.get("timestamp"),
                        ingested_at=obj.get("ingested_at"),
                        payload=obj.get("payload") or obj,
                    )
                except Exception:
                    logger.exception("Failed to parse raw record: %s", obj)
                    malformed += 1
                    continue

            try:
                norm = self.normalize(raw)
            except Exception:
                logger.exception("Normalization failed for record: %s", getattr(raw, "payload", raw))
                malformed += 1
                continue
            if not norm:
                continue
            if norm.id in seen_ids:
                continue
            seen_ids.add(norm.id)
            rows.append(norm.dict())

        if not rows:
            # still record checkpoint to avoid reprocessing empty file repeatedly
            self._checkpoints[key] = {"processed_at": datetime.now(timezone.utc).isoformat(), "written": 0, "parsed": parsed, "malformed": malformed}
            self._save_checkpoints()
            return 0

        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"]) if "timestamp" in df.columns else pd.to_datetime(df["timestamp"].fillna(pd.Timestamp.now()))

        # write parquet per-source/year/month/day
        written = 0
        output_files = []
        for (source, ts_date), g in df.groupby(["source", df["timestamp"].dt.date]):
            dt = pd.to_datetime(ts_date)
            year = dt.strftime("%Y")
            month = dt.strftime("%m")
            day = dt.strftime("%d")
            dest_dir = settings.PROCESSED_DIR / source / year / month / day
            dest_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{datetime.now(timezone.utc).strftime('%H%M%S')}-{int(datetime.now(timezone.utc).timestamp()*1000)}.parquet"
            path = dest_dir / filename
            try:
                g.to_parquet(path, index=False, engine="pyarrow")
                written += len(g)
                output_files.append(str(path))
                logger.info("Wrote %d records to %s", len(g), path)
            except Exception:
                logger.exception("Failed to write parquet to %s", path)

        # update checkpoint
        self._checkpoints[key] = {"processed_at": datetime.now(timezone.utc).isoformat(), "written": written, "parsed": parsed, "malformed": malformed, "outputs": output_files}
        self._save_checkpoints()

        return written

    def run(self, prefix: str | None = None, run_once: bool = False, max_objects: int | None = None):
        count = 0
        for key in self.list_objects(prefix=prefix):
            try:
                logger.info("Processing s3://%s/%s", self.bucket, key)
                self.process_key(key)
            except Exception:
                logger.exception("Error processing %s", key)
            count += 1
            if run_once or (max_objects and count >= max_objects):
                break


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--max-objects", type=int, default=None)
    args = parser.parse_args()
    S3Processor().run(prefix=args.prefix, run_once=args.run_once, max_objects=args.max_objects)
