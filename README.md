# Superset Experiment – Financial Crime Case Management

A self-contained environment to experiment with [Apache Superset](https://superset.apache.org/)
using a realistic **financial crime case-management** mock dataset spanning
**4 regions** and **17 markets**.

---

## What's included

| Component | Description |
|-----------|-------------|
| `docker-compose.yml` | Superset (web + worker + beat) + PostgreSQL + Redis |
| `superset/superset_config.py` | Pre-tuned Superset configuration |
| `data/schema.sql` | Financial crime database schema (star schema with views) |
| `data/mock_data.sql` | ~2 000 cases, ~4 900 alerts, ~10 000 transactions across 17 markets |
| `data/generate_mock_data.py` | Python script to regenerate / extend the mock dataset |
| `setup.sh` | One-shot bootstrap script |

---

## Prerequisites

| Requirement | Minimum version |
|-------------|-----------------|
| Docker Desktop (or Docker Engine + Compose) | 20.10+ |
| Python 3.8+ *(only if regenerating data)* | optional |
| 4 GB free RAM | – |
| 5 GB free disk | – |

---

## Quick start

```bash
# Clone the repo (if you haven't already)
git clone https://github.com/danalderslade/superset_experiment.git
cd superset_experiment

# Create your local .env from the example and set a strong secret key
cp .env.example .env
# Edit .env and replace the SECRET_KEY value with a random string, e.g.:
#   python3 -c "import secrets; print(secrets.token_urlsafe(42))"

# Run the one-shot setup (pulls images, starts services, creates admin user)
bash setup.sh
```

After the script completes, open **http://localhost:8088**
and log in with **admin / admin**.

### Manual start (alternative)

```bash
docker compose up -d
```

Then wait ~60 seconds for the `superset-init` container to finish before
opening the browser.

---

## Connecting to the financial crime dataset

1. In Superset go to **Settings → Database Connections → + Database**
2. Choose **PostgreSQL**
3. Enter the connection string:
   ```
   postgresql+psycopg2://analyst:analyst@mock_data_db:5432/financial_crime
   ```
4. Click **Test Connection**, then **Connect**

The database exposes the following objects:

### Dimension tables
| Table | Description |
|-------|-------------|
| `dim_region` | 4 regions (NOAM, EMEA, APAC, LATAM) |
| `dim_market` | 17 markets with currency codes |
| `dim_case_type` | 15 case types across AML, Fraud, Sanctions, Corruption |
| `dim_analyst` | 20 investigators distributed across markets |

### Fact tables
| Table | Description |
|-------|-------------|
| `fact_case` | ~2 000 cases with status, priority, risk score, dates |
| `fact_subject` | Individuals / entities linked to cases |
| `fact_alert` | ~4 900 alerts (transaction monitoring, screening, manual) |
| `fact_transaction` | ~10 000 transactions with amounts, currencies, countries |
| `fact_investigation_action` | ~8 000 workflow actions per case |

### Pre-built views (ready for Superset charts)
| View | Good for |
|------|----------|
| `vw_case_summary` | Case-level KPIs, heat-maps, pie charts |
| `vw_alert_summary` | Alert funnel, disposition rates |
| `vw_transaction_summary` | Transaction flow, suspicious-amount analysis |
| `vw_monthly_case_volume` | Time-series, trend lines |
| `vw_analyst_workload` | Team capacity charts |

---

## Regions and markets

| Region | Markets |
|--------|---------|
| **North America** | United States · Canada · Mexico |
| **Europe, Middle East & Africa** | UK · Germany · France · Netherlands · Switzerland · UAE · South Africa |
| **Asia Pacific** | Singapore · Hong Kong · Australia · Japan |
| **Latin America** | Brazil · Colombia · Chile |

---

## Suggested Superset dashboards

### 1 · Global Case Overview
- **Big number** – Total open cases
- **Big number** – SAR filed rate (%)
- **Bar chart** – Cases by region (stacked by category)
- **Pie chart** – Case status distribution
- **Heat-map** – Risk score by market

### 2 · Alert Intelligence
- **Funnel chart** – Alerts → Assigned → True Positive → Escalated
- **Line chart** – Monthly alert volume by alert type
- **Table** – Top 10 highest-value alerts

### 3 · Transaction Flow
- **World map** – Transaction flows by `from_country` / `to_country`
- **Bar chart** – Suspicious vs non-suspicious by channel
- **Histogram** – USD transaction amount distribution

### 4 · Analyst Workload
- **Bar chart** – Open cases per analyst
- **Scatter plot** – Avg risk score vs case count per analyst
- **Table** – Cases by team and priority

---

## Regenerating / extending mock data

```bash
# Produce a fresh mock_data.sql (tweak NUM_CASES or date ranges in the script)
python3 data/generate_mock_data.py > data/mock_data.sql

# Reload into the running container
docker compose exec mock_data_db \
  psql -U analyst -d financial_crime -f /docker-entrypoint-initdb.d/02_mock_data.sql
```

> **Tip:** Increase `NUM_CASES` at the top of `generate_mock_data.py` to scale
> the dataset, or change `START_DATE` / `END_DATE` to shift the time window.

---

## Stopping and resetting

```bash
# Stop all containers (data is preserved in Docker volumes)
docker compose down

# Full reset – removes all data volumes
docker compose down -v
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Docker Compose network                                      │
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │  superset    │   │  superset-   │   │ superset-worker │  │
│  │  :8088       │   │  worker-beat │   │  (Celery)       │  │
│  └──────┬───────┘   └──────┬───────┘   └────────┬────────┘  │
│         │                  │                     │           │
│  ┌──────▼──────────────────▼─────────────────────▼───────┐  │
│  │               Redis (cache / broker)                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────┐   ┌──────────────────────────┐   │
│  │  PostgreSQL: superset │   │  PostgreSQL:             │   │
│  │  (metadata store)     │   │  financial_crime         │   │
│  │                       │   │  (mock dataset)          │   │
│  └───────────────────────┘   └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port 8088 already in use | Change the left port in `docker-compose.yml`: `"8089:8088"` |
| Superset shows "DB connection error" | The init container may still be running – wait 60 s and refresh |
| `mock_data_db` missing tables | Check `docker compose logs mock_data_db` – the SQL scripts run automatically on first start |
| Slow first load | Images are ~1.5 GB total; subsequent starts are fast |
