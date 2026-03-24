# =============================================================================
# Apache Superset Configuration - Financial Crime Case Management POC
# =============================================================================
import os
from cachelib.redis import RedisCache

# ── Core ──────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    "postgresql+psycopg2://superset_user:superset_password@postgres:5432/superset"
)

# ── Feature flags ─────────────────────────────────────────────────────────────
FEATURE_FLAGS = {
    "ENABLE_EXPLORE_DRAG_AND_DROP":       True,
    "ENABLE_EXPLORE_JSON_CSRF_PROTECTION": False,
    "DASHBOARD_CROSS_FILTERS":            True,
    "DASHBOARD_RBAC":                     True,
    "EMBEDDED_SUPERSET":                  True,
    "ALERT_REPORTS":                      True,
    "DRILL_TO_DETAIL":                    True,
    "DRILL_BY":                           True,
    "ENABLE_TEMPLATE_PROCESSING":         True,   # Jinja in SQL
    "HORIZONTAL_FILTER_BAR":              True,
}

# ── Cache ─────────────────────────────────────────────────────────────────────
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

CACHE_CONFIG = {
    "CACHE_TYPE":            "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX":      "superset_",
    "CACHE_REDIS_URL":       REDIS_URL,
}

DATA_CACHE_CONFIG = {
    "CACHE_TYPE":            "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
    "CACHE_KEY_PREFIX":      "superset_results_",
    "CACHE_REDIS_URL":       REDIS_URL,
}

EXPLORE_FORM_DATA_CACHE_CONFIG = {
    "CACHE_TYPE":            "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX":      "superset_explore_",
    "CACHE_REDIS_URL":       REDIS_URL,
}

# ── Celery ────────────────────────────────────────────────────────────────────
class CeleryConfig:
    broker_url          = REDIS_URL
    imports             = ("superset.sql_lab", "superset.tasks.scheduler")
    result_backend      = REDIS_URL
    worker_prefetch_multiplier  = 1
    task_acks_late      = True
    task_annotations    = {
        "sql_lab.get_sql_results": {"rate_limit": "100/s"},
    }

CELERY_CONFIG = CeleryConfig

# ── SQL Lab ───────────────────────────────────────────────────────────────────
SQLLAB_TIMEOUT          = 300
SQLLAB_ASYNC_TIME_LIMIT_SEC = 300
SQL_MAX_ROW             = 100_000

# ── Viz ───────────────────────────────────────────────────────────────────────
ROW_LIMIT               = 50_000
VIZ_ROW_LIMIT           = 50_000

# ── Security ──────────────────────────────────────────────────────────────────
WTF_CSRF_ENABLED        = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE   = False   # Set True behind HTTPS in production
TALISMAN_ENABLED        = False   # Enable in production with proper CSP

# ── Roles ─────────────────────────────────────────────────────────────────────
# Custom roles are created via init_superset.sh
AUTH_ROLE_PUBLIC        = "Public"
AUTH_USER_REGISTRATION  = False

# ── Branding ─────────────────────────────────────────────────────────────────
APP_NAME                = "FCM Intelligence Hub"
APP_ICON                = "/static/assets/images/superset-logo-horiz.png"

# ── Timezone ─────────────────────────────────────────────────────────────────
# Analysts will filter by their local timezone; stored as UTC in DB.
SUPERSET_DEFAULT_TIMEZONE = "UTC"
