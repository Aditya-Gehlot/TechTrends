"""Generate small demo raw JSONL objects and upload to S3/MinIO for testing.

Uploads a few sample records for github, stackoverflow, google_trends and blogs
into the configured RAW_S3_BUCKET and prefix.
"""
import json
import logging
import random
from datetime import datetime

import boto3

from config import settings

logging.basicConfig(level=settings.LOG_LEVEL)


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.RAW_S3_REGION,
        endpoint_url=settings.RAW_S3_ENDPOINT_URL,
        aws_access_key_id=settings.RAW_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.RAW_S3_SECRET_ACCESS_KEY,
    )


def _upload(key: str, body: str):
    s3 = _s3_client()
    s3.put_object(Bucket=settings.RAW_S3_BUCKET, Key=key, Body=body.encode("utf-8"), ContentType="application/x-ndjson")
    logging.info("Uploaded demo object to s3://%s/%s", settings.RAW_S3_BUCKET, key)


def generate():
    now = datetime.utcnow()
    date_path = now.strftime("%Y/%m/%d")
    prefix = settings.RAW_S3_PREFIX.strip("/")

    # github events
    gh_key = f"{prefix}/github_events/{date_path}/{now.strftime('%H%M%S')}-{random.randint(1000,9999)}.jsonl"
    gh_lines = []
    for i in range(5):
        ev = {
            "id": str(random.randint(1000000, 9999999)),
            "type": "PushEvent",
            "repo": {"name": "example/repo"},
            "actor": {"id": random.randint(1000, 9999), "login": f"dev{random.randint(1,99)}"},
        }
        line = json.dumps({"topic": settings.GITHUB_TOPIC, "partition": 0, "offset": i, "timestamp": int(now.timestamp() * 1000), "ingested_at": now.isoformat(), "payload": ev})
        gh_lines.append(line)
    _upload(gh_key, "\n".join(gh_lines) + "\n")

    # stackoverflow
    so_key = f"{prefix}/stackoverflow/{date_path}/{now.strftime('%H%M%S')}-{random.randint(1000,9999)}.jsonl"
    so_lines = []
    for i in range(3):
        q = {"question_id": random.randint(2000000, 2999999), "title": "How to use async in python?", "tags": ["python", "asyncio"], "creation_date": int(now.timestamp())}
        so_lines.append(json.dumps({"topic": settings.STACKOVERFLOW_TOPIC, "partition": 0, "offset": i, "timestamp": int(now.timestamp() * 1000), "ingested_at": now.isoformat(), "payload": q}))
    _upload(so_key, "\n".join(so_lines) + "\n")

    # google trends (values for keywords)
    gt_key = f"{prefix}/google_trends/{date_path}/{now.strftime('%H%M%S')}-{random.randint(1000,9999)}.jsonl"
    vals = []
    for kw in settings.PYTRENDS_KEYWORDS:
        vals.append({"term": kw, "value": random.randint(0, 100)})
    gt_payload = {"timestamp": now.isoformat(), "values": vals}
    _upload(gt_key, json.dumps({"topic": settings.GOOGLE_TRENDS_TOPIC, "partition": 0, "offset": 0, "timestamp": int(now.timestamp() * 1000), "ingested_at": now.isoformat(), "payload": gt_payload}) + "\n")

    # blogs
    blog_key = f"{prefix}/tech_blogs/{date_path}/{now.strftime('%H%M%S')}-{random.randint(1000,9999)}.jsonl"
    blog_lines = []
    for i in range(2):
        b = {"id": f"post-{random.randint(1000,9999)}", "title": "Announcing great new tech", "summary": "A new library for distributed systems.", "link": "https://example.com/article", "published": now.isoformat()}
        blog_lines.append(json.dumps({"topic": settings.BLOG_TOPIC, "partition": 0, "offset": i, "timestamp": int(now.timestamp() * 1000), "ingested_at": now.isoformat(), "payload": b}))
    _upload(blog_key, "\n".join(blog_lines) + "\n")


if __name__ == "__main__":
    generate()
