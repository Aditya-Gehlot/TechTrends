import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
STATE_DIR = Path(os.environ.get("STATE_DIR", BASE_DIR / ".state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Kafka
BOOTSTRAP_SERVERS = os.environ.get("BOOTSTRAP_SERVERS", "localhost:9092")

# Topics
GOOGLE_TRENDS_TOPIC = os.environ.get("GOOGLE_TRENDS_TOPIC", "google_trends")
STACKOVERFLOW_TOPIC = os.environ.get("STACKOVERFLOW_TOPIC", "stackoverflow")
GITHUB_TOPIC = os.environ.get("GITHUB_TOPIC", "github_events")
BLOG_TOPIC = os.environ.get("BLOG_TOPIC", "tech_blogs")

# Intervals (seconds)
GOOGLE_TRENDS_INTERVAL = int(os.environ.get("GOOGLE_TRENDS_INTERVAL", 300))
STACKOVERFLOW_INTERVAL = int(os.environ.get("STACKOVERFLOW_INTERVAL", 60))
GITHUB_INTERVAL = int(os.environ.get("GITHUB_INTERVAL", 30))
BLOG_INTERVAL = int(os.environ.get("BLOG_INTERVAL", 300))

# APIs
STACKOVERFLOW_PAGE_SIZE = int(os.environ.get("STACKOVERFLOW_PAGE_SIZE", 50))
STACKOVERFLOW_API_URL = os.environ.get("STACKOVERFLOW_API_URL", "https://api.stackexchange.com/2.3/questions")
GITHUB_EVENTS_URL = os.environ.get("GITHUB_EVENTS_URL", "https://api.github.com/events")
BLOG_FEEDS = os.environ.get("BLOG_FEEDS", "https://dev.to/feed").split(",")

# Pytrends keywords (comma separated list)
PYTRENDS_KEYWORDS = os.environ.get("PYTRENDS_KEYWORDS", "python,rust,kubernetes,docker,spark").split(",")
PYTRENDS_TIMEOUT_SECONDS = int(os.environ.get("PYTRENDS_TIMEOUT_SECONDS", 10))
PYTRENDS_RETRIES = int(os.environ.get("PYTRENDS_RETRIES", 2))
PYTRENDS_BACKOFF_FACTOR = float(os.environ.get("PYTRENDS_BACKOFF_FACTOR", 0.5))

# Optional tokens
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# S3 / object storage
RAW_S3_BUCKET = os.environ.get("RAW_S3_BUCKET")
RAW_S3_PREFIX = os.environ.get("RAW_S3_PREFIX", "raw")
RAW_S3_REGION = os.environ.get("RAW_S3_REGION", "us-east-1")
RAW_S3_ENDPOINT_URL = os.environ.get("RAW_S3_ENDPOINT_URL")
RAW_S3_ACCESS_KEY_ID = os.environ.get("RAW_S3_ACCESS_KEY_ID")
RAW_S3_SECRET_ACCESS_KEY = os.environ.get("RAW_S3_SECRET_ACCESS_KEY")
RAW_S3_BATCH_SIZE = int(os.environ.get("RAW_S3_BATCH_SIZE", 100))
RAW_S3_FLUSH_INTERVAL = int(os.environ.get("RAW_S3_FLUSH_INTERVAL", 60))

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Processed data, feature store and ML paths
PROCESSED_DIR = Path(os.environ.get("PROCESSED_DIR", BASE_DIR / "processed"))
FEATURE_STORE_DIR = Path(os.environ.get("FEATURE_STORE_DIR", BASE_DIR / "feature_store"))
ML_MODELS_DIR = Path(os.environ.get("ML_MODELS_DIR", BASE_DIR / "ml" / "models"))
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
FEATURE_WINDOW_DAYS = int(os.environ.get("FEATURE_WINDOW_DAYS", 7))

# Ensure directories exist
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
FEATURE_STORE_DIR.mkdir(parents=True, exist_ok=True)
ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
