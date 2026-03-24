#!/usr/bin/env python3
"""
Superset API Bootstrap Script
Connects to a running Superset instance and:
  1. Registers the FCM database connection
  2. Creates all virtual datasets
  3. Creates all charts
  4. Creates and assembles all dashboards

Prerequisites:
  pip install requests
  Superset must be running at SUPERSET_URL (default http://localhost:8088)

Usage:
  python scripts/bootstrap_superset.py
  SUPERSET_URL=http://my-host:8088 python scripts/bootstrap_superset.py
"""

import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://localhost:8088").rstrip("/")
ADMIN_USER   = os.environ.get("SUPERSET_ADMIN_USERNAME", "admin")
ADMIN_PASS   = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")
FCM_DB_URI   = os.environ.get(
    "FCM_DB_URI",
    "postgresql+psycopg2://fcm_user:fcm_password@localhost:5432/fcm_poc"
)

SESSION = requests.Session()


# ── Auth ──────────────────────────────────────────────────────────────────────

def login():
    resp = SESSION.post(f"{SUPERSET_URL}/api/v1/security/login", json={
        "username": ADMIN_USER,
        "password": ADMIN_PASS,
        "provider": "db",
        "refresh": True,
    })
    resp.raise_for_status()
    token = resp.json()["access_token"]
    SESSION.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    })
    # CSRF
    csrf_resp = SESSION.get(f"{SUPERSET_URL}/api/v1/security/csrf_token/")
    csrf_resp.raise_for_status()
    SESSION.headers["X-CSRFToken"] = csrf_resp.json()["result"]
    print("✓ Authenticated with Superset")


# ── Database connection ────────────────────────────────────────────────────────

def register_database():
    payload = {
        "database_name": "FCM Case Management DB",
        "sqlalchemy_uri": FCM_DB_URI,
        "engine": "postgresql",
        "expose_in_sqllab": True,
        "allow_run_async": True,
        "allow_ctas": False,
        "allow_cvas": False,
        "allow_dml": False,
        "force_ctas_schema": None,
        "extra": json.dumps({
            "metadata_params": {},
            "engine_params": {},
            "metadata_cache_timeout": {},
            "schemas_allowed_for_file_upload": []
        }),
    }
    resp = SESSION.post(f"{SUPERSET_URL}/api/v1/database/", json=payload)
    if resp.status_code == 422 and "already exists" in resp.text:
        print("  Database already registered, fetching ID …")
        r = SESSION.get(f"{SUPERSET_URL}/api/v1/database/?q=(filters:!((col:database_name,opr:eq,value:'FCM Case Management DB')))")
        db_id = r.json()["result"][0]["id"]
    else:
        resp.raise_for_status()
        db_id = resp.json()["id"]
    print(f"✓ FCM database ID: {db_id}")
    return db_id


# ── Virtual datasets ──────────────────────────────────────────────────────────

DATASETS = {
    "vw_case_operational_summary": {
        "sql_file": "superset/datasets/virtual_datasets.sql",
        "marker":   "-- DATASET 1:",
        "next":     "-- DATASET 2:",
    },
    "vw_sla_performance": {
        "sql_file": "superset/datasets/virtual_datasets.sql",
        "marker":   "-- DATASET 2:",
        "next":     "-- DATASET 3:",
    },
    "vw_workflow_funnel": {
        "sql_file": "superset/datasets/virtual_datasets.sql",
        "marker":   "-- DATASET 3:",
        "next":     "-- DATASET 4:",
    },
    "vw_case_volume_trend": {
        "sql_file": "superset/datasets/virtual_datasets.sql",
        "marker":   "-- DATASET 4:",
        "next":     "-- DATASET 5:",
    },
    "vw_team_workload": {
        "sql_file": "superset/datasets/virtual_datasets.sql",
        "marker":   "-- DATASET 5:",
        "next":     "-- DATASET 6:",
    },
    "vw_sar_intelligence": {
        "sql_file": "superset/datasets/virtual_datasets.sql",
        "marker":   "-- DATASET 6:",
        "next":     "-- DATASET 7:",
    },
    "vw_alert_to_case_conversion": {
        "sql_file": "superset/datasets/virtual_datasets.sql",
        "marker":   "-- DATASET 7:",
        "next":     "-- DATASET 8:",
    },
    "vw_financial_exposure": {
        "sql_file": "superset/datasets/virtual_datasets.sql",
        "marker":   "-- DATASET 8:",
        "next":     None,
    },
}


def _extract_sql(sql_file: str, marker: str, next_marker) -> str:
    """Slice a block of SQL between two comment markers."""
    text = Path(sql_file).read_text()
    start = text.index(marker)
    if next_marker:
        end = text.index(next_marker, start)
        block = text[start:end]
    else:
        block = text[start:]
    # Strip the comment header line and trailing whitespace
    lines = block.splitlines()
    sql_lines = [l for l in lines if not l.startswith("-- DATASET")]
    sql = "\n".join(sql_lines).strip()
    # Remove all semicolons — Superset rejects multi-statement SQL
    sql = sql.replace(";", "")
    # Remove trailing comment-only lines
    result_lines = sql.splitlines()
    while result_lines and result_lines[-1].strip().startswith("--"):
        result_lines.pop()
    return "\n".join(result_lines).strip()


def create_datasets(db_id: int) -> dict:
    """Returns {dataset_name: dataset_id}"""
    dataset_ids = {}
    for name, cfg in DATASETS.items():
        sql = _extract_sql(cfg["sql_file"], cfg["marker"], cfg["next"])
        payload = {
            "database": db_id,
            "schema":   "public",
            "sql":      sql,
            "table_name": name,
        }
        resp = SESSION.post(f"{SUPERSET_URL}/api/v1/dataset/", json=payload)
        if resp.status_code in (200, 201):
            ds_id = resp.json()["id"]
            print(f"  ✓ Dataset created: {name} (id={ds_id})")
        elif resp.status_code == 422:
            # Already exists - look it up
            r = SESSION.get(
                f"{SUPERSET_URL}/api/v1/dataset/?q=(filters:!((col:table_name,opr:eq,value:'{name}')))"
            )
            result = r.json().get("result", [])
            ds_id = result[0]["id"] if result else None
            print(f"  ~ Dataset exists:  {name} (id={ds_id})")
        else:
            print(f"  ✗ Dataset failed:  {name} — {resp.status_code} {resp.text[:200]}")
            ds_id = None
        dataset_ids[name] = ds_id
    return dataset_ids


# ── Charts ────────────────────────────────────────────────────────────────────
# Each chart definition maps to a Superset viz_type and slice configuration.

def build_charts(dataset_ids: dict) -> dict:
    """Returns {chart_slug: chart_id}"""
    chart_ids = {}
    charts = _get_chart_definitions(dataset_ids)
    for chart in charts:
        name = chart.pop("_name")
        resp = SESSION.post(f"{SUPERSET_URL}/api/v1/chart/", json=chart)
        if resp.status_code in (200, 201):
            cid = resp.json()["id"]
            print(f"  ✓ Chart: {name} (id={cid})")
        elif resp.status_code == 422:
            r = SESSION.get(
                f"{SUPERSET_URL}/api/v1/chart/?q=(filters:!((col:slice_name,opr:eq,value:'{name}')))"
            )
            result = r.json().get("result", [])
            cid = result[0]["id"] if result else None
            print(f"  ~ Chart exists: {name}")
        else:
            print(f"  ✗ Chart failed: {name} — {resp.status_code} {resp.text[:200]}")
            cid = None
        chart_ids[name] = cid
    return chart_ids


def _get_chart_definitions(ds: dict) -> list:
    """
    Returns minimal chart payloads understood by the Superset REST API.
    Each chart references a dataset by id and specifies viz_type + params.
    """
    op = ds.get("vw_case_operational_summary")
    sla = ds.get("vw_sla_performance")
    wf  = ds.get("vw_workflow_funnel")
    tw  = ds.get("vw_team_workload")
    ci  = ds.get("vw_case_operational_summary")
    fe  = ds.get("vw_financial_exposure")
    sar = ds.get("vw_sar_intelligence")
    alt = ds.get("vw_alert_to_case_conversion")

    def params(d): return json.dumps(d)

    return [
        # ── KPI Big Numbers ──────────────────────────────────────────────────
        {
            "_name": "total_open_cases",
            "slice_name": "Total Open Cases",
            "viz_type": "big_number_total",
            "datasource_id": op, "datasource_type": "table",
            "params": params({
                "metric": {"aggregate":"COUNT","column":{"column_name":"case_id"},"expressionType":"SIMPLE","label":"COUNT(case_id)"},
                "adhoc_filters": [{"clause":"WHERE","expressionType":"SQL","sqlExpression":"case_status NOT IN ('closed','withdrawn')"}],
                "subheader": "currently open"
            })
        },
        {
            "_name": "sla_breached_count",
            "slice_name": "SLA Breached (Open)",
            "viz_type": "big_number_total",
            "datasource_id": op, "datasource_type": "table",
            "params": params({
                "metric": {"aggregate":"COUNT","column":{"column_name":"case_id"},"expressionType":"SIMPLE","label":"Cases"},
                "adhoc_filters": [{"clause":"WHERE","expressionType":"SQL","sqlExpression":"is_sla_breached = true AND case_status NOT IN ('closed','withdrawn')"}],
                "subheader": "open & SLA breached"
            })
        },
        {
            "_name": "escalated_count",
            "slice_name": "Escalated Cases",
            "viz_type": "big_number_total",
            "datasource_id": op, "datasource_type": "table",
            "params": params({
                "metric": {"aggregate":"COUNT","column":{"column_name":"case_id"},"expressionType":"SIMPLE","label":"Cases"},
                "adhoc_filters": [{"clause":"WHERE","expressionType":"SQL","sqlExpression":"case_status = 'escalated'"}],
                "subheader": "currently escalated"
            })
        },
        {
            "_name": "pending_sar_count",
            "slice_name": "Pending SAR Decision",
            "viz_type": "big_number_total",
            "datasource_id": op, "datasource_type": "table",
            "params": params({
                "metric": {"aggregate":"COUNT","column":{"column_name":"case_id"},"expressionType":"SIMPLE","label":"Cases"},
                "adhoc_filters": [{"clause":"WHERE","expressionType":"SQL","sqlExpression":"case_status = 'pending_sar'"}],
                "subheader": "awaiting SAR decision"
            })
        },
        {
            "_name": "closed_today_count",
            "slice_name": "Closed Today",
            "viz_type": "big_number_total",
            "datasource_id": op, "datasource_type": "table",
            "params": params({
                "metric": {"aggregate":"COUNT","column":{"column_name":"case_id"},"expressionType":"SIMPLE","label":"Cases"},
                "adhoc_filters": [{"clause":"WHERE","expressionType":"SQL","sqlExpression":"closed_date = CURRENT_DATE"}],
                "subheader": "closed today"
            })
        },

        # ── Workflow / Pipeline ──────────────────────────────────────────────
        {
            "_name": "workflow_funnel",
            "slice_name": "Workflow Pipeline (Funnel)",
            "viz_type": "funnel",
            "datasource_id": wf, "datasource_type": "table",
            "params": params({
                "groupby": ["workflow_stage"],
                "metric":  {"aggregate":"SUM","column":{"column_name":"case_count"},"expressionType":"SIMPLE","label":"Cases"},
                "sort_by_metric": True
            })
        },
        {
            "_name": "cases_by_stage_bar",
            "slice_name": "Cases by Workflow Stage",
            "viz_type": "bar",
            "datasource_id": wf, "datasource_type": "table",
            "params": params({
                "groupby": ["workflow_stage"],
                "metrics": [{"aggregate":"SUM","column":{"column_name":"case_count"},"expressionType":"SIMPLE","label":"Cases"}],
                "x_axis_sort": "stage_order",
                "color_scheme": "googleCategory20b"
            })
        },

        # ── Region / Team ────────────────────────────────────────────────────
        {
            "_name": "cases_by_region_map",
            "slice_name": "Open Cases by Country (Map)",
            "viz_type": "world_map",
            "datasource_id": op, "datasource_type": "table",
            "params": params({
                "entity": "country_code",
                "metric": {"aggregate":"COUNT","column":{"column_name":"case_id"},"expressionType":"SIMPLE","label":"Cases"},
                "adhoc_filters": [{"clause":"WHERE","expressionType":"SQL","sqlExpression":"case_status NOT IN ('closed','withdrawn')"}]
            })
        },
        {
            "_name": "open_cases_by_team",
            "slice_name": "Open Cases by Team",
            "viz_type": "bar",
            "datasource_id": op, "datasource_type": "table",
            "params": params({
                "groupby": ["team_name"],
                "metrics": [{"aggregate":"COUNT","column":{"column_name":"case_id"},"expressionType":"SIMPLE","label":"Cases"}],
                "adhoc_filters": [{"clause":"WHERE","expressionType":"SQL","sqlExpression":"case_status NOT IN ('closed','withdrawn')"}],
                "order_desc": True,
                "limit": 20,
                "color_scheme": "bnbColors"
            })
        },

        # ── Crime / Risk ─────────────────────────────────────────────────────
        {
            "_name": "cases_by_crime_category",
            "slice_name": "Cases by Crime Category",
            "viz_type": "pie",
            "datasource_id": op, "datasource_type": "table",
            "params": params({
                "groupby": ["crime_category"],
                "metric":  {"aggregate":"COUNT","column":{"column_name":"case_id"},"expressionType":"SIMPLE","label":"Cases"},
                "donut": True,
                "show_labels": True
            })
        },
        {
            "_name": "sla_compliance_gauge",
            "slice_name": "SLA Compliance Rate",
            "viz_type": "gauge_chart",
            "datasource_id": sla, "datasource_type": "table",
            "params": params({
                "metric": {"aggregate":"AVG","column":{"column_name":"sla_compliance_pct"},"expressionType":"SIMPLE","label":"SLA %"},
                "min_val": 0,
                "max_val": 100,
                "start_angle": 225,
                "end_angle": -45
            })
        },

        # ── Time Series ──────────────────────────────────────────────────────
        {
            "_name": "daily_case_volume_line",
            "slice_name": "Daily Case Volume: Opened vs Closed",
            "viz_type": "echarts_timeseries_line",
            "datasource_id": sla, "datasource_type": "table",
            "params": params({
                "x_axis": "cohort_month",
                "metrics": [
                    {"aggregate":"SUM","column":{"column_name":"total_cases"},"expressionType":"SIMPLE","label":"Opened"},
                    {"aggregate":"SUM","column":{"column_name":"closed_cases"},"expressionType":"SIMPLE","label":"Closed"}
                ],
                "groupby": ["region_name"]
            })
        },

        # ── Drill-down table ─────────────────────────────────────────────────
        {
            "_name": "open_cases_drill_table",
            "slice_name": "Open Cases — Detail Table",
            "viz_type": "table",
            "datasource_id": op, "datasource_type": "table",
            "params": params({
                "all_columns": [
                    "case_reference","case_status","workflow_stage","risk_level",
                    "priority_name","crime_type_name","crime_category",
                    "team_name","analyst_name","region_name","country_name",
                    "opened_date","review_due_date","actual_days_open",
                    "sla_status_label","age_band","estimated_value_usd",
                    "involves_pep","involves_sanctioned_entity","cross_border"
                ],
                "adhoc_filters": [{"clause":"WHERE","expressionType":"SQL","sqlExpression":"case_status NOT IN ('closed','withdrawn')"}],
                "order_by_cols": ["[\"actual_days_open\", false]"],
                "page_length": 25,
                "include_search": True
            })
        },

        # ── SLA Analytics ────────────────────────────────────────────────────
        {
            "_name": "sla_compliance_by_team_bar",
            "slice_name": "SLA Compliance % by Team",
            "viz_type": "bar",
            "datasource_id": sla, "datasource_type": "table",
            "params": params({
                "groupby": ["team_name"],
                "metrics": [{"aggregate":"AVG","column":{"column_name":"sla_compliance_pct"},"expressionType":"SIMPLE","label":"SLA %"}],
                "limit": 20, "order_desc": False
            })
        },
        {
            "_name": "avg_days_open_heatmap",
            "slice_name": "Avg Days Open: Team × Risk Level",
            "viz_type": "heatmap",
            "datasource_id": sla, "datasource_type": "table",
            "params": params({
                "all_columns_x": "team_name",
                "all_columns_y": "risk_level",
                "metric": {"aggregate":"AVG","column":{"column_name":"avg_days_open"},"expressionType":"SIMPLE","label":"Avg Days"}
            })
        },

        # ── Team Workload ────────────────────────────────────────────────────
        {
            "_name": "cases_per_fte_bar",
            "slice_name": "Open Cases per FTE by Team",
            "viz_type": "bar",
            "datasource_id": tw, "datasource_type": "table",
            "params": params({
                "groupby": ["team_name"],
                "metrics": [{"aggregate":"AVG","column":{"column_name":"cases_per_fte"},"expressionType":"SIMPLE","label":"Cases/FTE"}],
                "order_desc": True, "limit": 15
            })
        },
        {
            "_name": "analyst_workload_table",
            "slice_name": "Analyst Workload Table",
            "viz_type": "table",
            "datasource_id": tw, "datasource_type": "table",
            "params": params({
                "all_columns": [
                    "analyst_name","grade","team_name","team_type","region_name",
                    "open_cases","escalated_cases","sla_breached_open",
                    "critical_open_cases","avg_open_case_age","cases_per_fte"
                ],
                "order_by_cols": ["[\"open_cases\", false]"],
                "page_length": 50,
                "include_search": True
            })
        },

        # ── Financial Exposure ───────────────────────────────────────────────
        {
            "_name": "value_at_risk_by_region",
            "slice_name": "Estimated Value at Risk by Region",
            "viz_type": "bar",
            "datasource_id": fe, "datasource_type": "table",
            "params": params({
                "groupby": ["region_name"],
                "metrics": [{"aggregate":"SUM","column":{"column_name":"total_estimated_usd"},"expressionType":"SIMPLE","label":"USD at Risk"}],
                "order_desc": True
            })
        },
        {
            "_name": "loss_vs_recovered_stacked",
            "slice_name": "Confirmed Loss vs Recovered by Quarter",
            "viz_type": "echarts_timeseries_bar",
            "datasource_id": fe, "datasource_type": "table",
            "params": params({
                "x_axis": "opened_quarter",
                "metrics": [
                    {"aggregate":"SUM","column":{"column_name":"total_confirmed_loss_usd"},"expressionType":"SIMPLE","label":"Confirmed Loss"},
                    {"aggregate":"SUM","column":{"column_name":"total_recovered_usd"},"expressionType":"SIMPLE","label":"Recovered"}
                ],
                "stack": True
            })
        },

        # ── SAR Intelligence ─────────────────────────────────────────────────
        {
            "_name": "sar_by_authority_bar",
            "slice_name": "SARs Filed by Reporting Authority",
            "viz_type": "bar",
            "datasource_id": sar, "datasource_type": "table",
            "params": params({
                "groupby": ["reporting_authority"],
                "metrics": [{"aggregate":"COUNT","column":{"column_name":"sar_id"},"expressionType":"SIMPLE","label":"SARs"}],
                "order_desc": True
            })
        },
    ]


# ── Dashboards ────────────────────────────────────────────────────────────────

def create_dashboard(title: str, slug: str, description: str) -> int:
    payload = {
        "dashboard_title": title,
        "slug":            slug,
        "published":       True,
    }
    resp = SESSION.post(f"{SUPERSET_URL}/api/v1/dashboard/", json=payload)
    if resp.status_code in (200, 201):
        did = resp.json()["id"]
        print(f"  ✓ Dashboard: {title} (id={did})")
        return did
    elif resp.status_code == 422:
        r = SESSION.get(
            f"{SUPERSET_URL}/api/v1/dashboard/?q=(filters:!((col:slug,opr:eq,value:'{slug}')))"
        )
        result = r.json().get("result", [])
        did = result[0]["id"] if result else None
        print(f"  ~ Dashboard exists: {title}")
        return did
    else:
        print(f"  ✗ Dashboard failed: {title} — {resp.status_code}")
        return None


def add_charts_to_dashboard(dashboard_id: int, chart_ids: list):
    if not dashboard_id:
        return
    valid_ids = [c for c in chart_ids if c]
    if not valid_ids:
        print(f"    ~ No valid chart IDs for dashboard {dashboard_id}")
        return

    # Build a position_json grid layout — each chart gets a CHART component
    # arranged in rows of 2 (each 6 columns wide out of 12)
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"children": ["GRID_ID"], "id": "ROOT_ID", "type": "ROOT"},
        "GRID_ID": {"children": [], "id": "GRID_ID", "type": "GRID", "parents": ["ROOT_ID"]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": ""}},
    }
    row_idx = 0
    for i, cid in enumerate(valid_ids):
        col_in_row = i % 2
        if col_in_row == 0:
            row_id = f"ROW-{row_idx}"
            position[row_id] = {
                "children": [],
                "id": row_id,
                "type": "ROW",
                "parents": ["ROOT_ID", "GRID_ID"],
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
            }
            position["GRID_ID"]["children"].append(row_id)

        chart_key = f"CHART-{cid}"
        position[chart_key] = {
            "children": [],
            "id": chart_key,
            "type": "CHART",
            "parents": ["ROOT_ID", "GRID_ID", row_id],
            "meta": {
                "chartId": cid,
                "width": 6,
                "height": 50,
                "sliceName": "",
            },
        }
        position[row_id]["children"].append(chart_key)

        if col_in_row == 1:
            row_idx += 1
    # Close final row if odd number of charts
    if len(valid_ids) % 2 == 1:
        row_idx += 1

    # json_metadata references default_filters and chart IDs
    json_metadata = json.dumps({
        "timed_refresh_immune_slices": [],
        "expanded_slices": {},
        "refresh_frequency": 0,
        "default_filters": "{}",
        "color_scheme": "",
        "label_colors": {},
        "shared_label_colors": {},
        "cross_filters_enabled": True,
    })

    resp = SESSION.put(f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}", json={
        "position_json": json.dumps(position),
        "json_metadata": json_metadata,
    })
    if resp.status_code in (200, 201):
        print(f"    ✓ Added {len(valid_ids)} charts to dashboard {dashboard_id}")
    else:
        print(f"    ✗ Could not add charts: {resp.status_code} {resp.text[:200]}")


# ── Entry point ───────────────────────────────────────────────────────────────

def wait_for_superset(retries=12, delay=10):
    print(f"Waiting for Superset at {SUPERSET_URL} …")
    for i in range(retries):
        try:
            r = requests.get(f"{SUPERSET_URL}/health", timeout=5)
            if r.status_code == 200:
                print("  Superset is up.")
                return True
        except requests.exceptions.ConnectionError:
            pass
        print(f"  Retry {i+1}/{retries} in {delay}s …")
        time.sleep(delay)
    return False


def main():
    if not wait_for_superset():
        print("Could not reach Superset. Aborting.")
        sys.exit(1)

    login()

    print("\n── Registering database ──")
    db_id = register_database()

    print("\n── Creating datasets ──")
    dataset_ids = create_datasets(db_id)

    print("\n── Creating charts ──")
    chart_ids = build_charts(dataset_ids)

    print("\n── Creating dashboards ──")
    dashboards = [
        ("FCM: Operational Overview",    "fcm-operational-overview", "Real-time case pipeline overview",
         ["total_open_cases","sla_breached_count","escalated_count","pending_sar_count","closed_today_count",
          "workflow_funnel","cases_by_stage_bar","cases_by_region_map","open_cases_by_team",
          "cases_by_crime_category","sla_compliance_gauge","daily_case_volume_line","open_cases_drill_table"]),

        ("FCM: SLA & Performance",       "fcm-sla-performance", "SLA compliance and breach analysis",
         ["sla_compliance_by_team_bar","avg_days_open_heatmap","daily_case_volume_line"]),

        ("FCM: Team & Analyst Workload", "fcm-team-workload",   "Analyst capacity and caseload",
         ["cases_per_fte_bar","analyst_workload_table"]),

        ("FCM: Financial Exposure",      "fcm-financial-exposure","Value at risk and recovery",
         ["value_at_risk_by_region","loss_vs_recovered_stacked","sar_by_authority_bar"]),
    ]

    for title, slug, desc, chart_names in dashboards:
        did = create_dashboard(title, slug, desc)
        ids = [chart_ids.get(n) for n in chart_names]
        add_charts_to_dashboard(did, ids)

    print("\n✓ Bootstrap complete. Open http://localhost:8088 and log in as admin/admin.")


if __name__ == "__main__":
    main()
