"""Smoke demo: upload demo data, run pipeline, and print quick summary.

Usage: python scripts/smoke_demo.py
"""
import logging
import time
import requests

from config import settings
from scripts.generate_demo_data import generate as gen_demo
from scripts.run_pipeline import main as run_pipeline

logging.basicConfig(level=settings.LOG_LEVEL)


def main():
    print("Uploading demo data to S3...")
    gen_demo()
    time.sleep(1)
    print("Running processing -> features -> training pipeline")
    run_pipeline()
    print("Pipeline complete. If API is running, you can check /trends/top")
    api = getattr(settings, "API_URL", "http://localhost:8000")
    try:
        r = requests.get(f"{api}/trends/top")
        print("API response:", r.status_code, r.text[:200])
    except Exception as e:
        print("Could not reach API at", api, "— start it separately with: uvicorn api.app:app --reload")


if __name__ == "__main__":
    main()
