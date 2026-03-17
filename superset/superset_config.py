# Superset configuration for local experiment environment

import os
from celery.schedules import crontab
from flask_caching.backends.filesystemcache import FileSystemCache

# ---------------------------------------------------
# Database (metadata store)
# ---------------------------------------------------
DATABASE_USER = os.environ.get("DATABASE_USER", "superset")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "superset")
DATABASE_HOST = os.environ.get("DATABASE_HOST", "db")
DATABASE_PORT = os.environ.get("DATABASE_PORT", "5432")
DATABASE_DB = os.environ.get("DATABASE_DB", "superset")

SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}"
    f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

# ---------------------------------------------------
# Secret key – MUST be set via the SECRET_KEY environment variable.
# Generate a strong value with:
#   python3 -c "import secrets; print(secrets.token_urlsafe(42))"
# See .env.example for configuration guidance.
# ---------------------------------------------------
SECRET_KEY = os.environ["SECRET_KEY"]

# ---------------------------------------------------
# Redis / Celery
# ---------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_CELERY_DB = int(os.environ.get("REDIS_CELERY_DB", "0"))
REDIS_RESULTS_DB = int(os.environ.get("REDIS_RESULTS_DB", "1"))

RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}

DATA_CACHE_CONFIG = CACHE_CONFIG

class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
    )
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    worker_prefetch_multiplier = 10
    task_acks_late = True
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

# ---------------------------------------------------
# Feature flags
# ---------------------------------------------------
FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# ---------------------------------------------------
# Security / CORS (permissive for local dev)
# ---------------------------------------------------
WTF_CSRF_ENABLED = True
TALISMAN_ENABLED = False
