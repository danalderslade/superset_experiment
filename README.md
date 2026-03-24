# FCM Intelligence Hub — Apache Superset POC

A proof-of-concept **Financial Crime Case Management** analytics platform built on Apache Superset. Designed for a multi-regional, multi-national bank to give operations teams self-service MI dashboards.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Apache Superset  :8088                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  6 pre-built dashboards (self-service templates) │   │
│  │  8 virtual datasets (saved SQL)                  │   │
│  │  Native filters, cross-filter, drill-to-detail   │   │
│  └────────────────────┬─────────────────────────────┘   │
│                        │ read-only SQL                    │
│  ┌─────────────────────▼──────────────┐                  │
│  │  PostgreSQL 16  :5432              │                  │
│  │  ├─ fcm_poc   (FCM warehouse)      │                  │
│  │  │   ├─ fact_case                  │                  │
│  │  │   ├─ fact_case_stage_history    │                  │
│  │  │   ├─ fact_sar                   │                  │
│  │  │   ├─ fact_alert                 │                  │
│  │  │   ├─ agg_daily_case_snapshot    │                  │
│  │  │   └─ 10× dim_* tables           │                  │
│  │  └─ superset  (Superset metadata)  │                  │
│  └────────────────────────────────────┘                  │
│  Redis :6379 (cache + Celery broker)                     │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker Desktop (or Docker Engine + Compose plugin) ≥ 24
- 8 GB RAM available for containers

### 1 — Clone and start

```bash
git clone <this-repo>
cd superset_experiment
docker compose up -d
```

The first run takes ~5 minutes while it:
1. Starts PostgreSQL and Redis
2. Creates both databases and user accounts
3. Loads the FCM schema (`db/01_schema.sql`)
4. Seeds all reference data (`db/02_seed_reference_data.sql`)
5. Generates **5,000 synthetic cases**, 15,000 alerts and associated SARs
6. Starts Superset and runs database + role init

### 2 — Bootstrap Superset

Once `docker compose ps` shows `fcm_superset` as **healthy**:

```bash
pip install requests
python scripts/bootstrap_superset.py
```

This registers the FCM database, creates all datasets and charts, and assembles dashboards.

### 3 — Open the hub

Go to [http://localhost:8088](http://localhost:8088) and log in:

| Username | Password |
|----------|----------|
| `admin`  | `admin`  |

Navigate to **Dashboards** to see all six pre-built views.

---

## Dashboards

| Dashboard | Purpose |
|-----------|---------|
| **FCM: Operational Overview** | Primary ops screen: KPI tiles, workflow funnel, regional map, daily trend, drill-down case table |
| **FCM: SLA & Performance** | SLA compliance % by team/region/risk level, breach root-cause, P90 age, throughput |
| **FCM: Team & Analyst Workload** | Cases per FTE, analyst heatmap, critical case distribution, capacity risk |
| **FCM: Crime Type Intelligence** | Typology treemap, channel × crime heatmap, PEP/sanctions flags, alert conversion rates |
| **FCM: Financial Exposure & Recovery** | Value at risk, confirmed loss, recovery %, SAR intelligence, DAML consent |
| **FCM: Executive Summary** | One-page senior management view: global KPIs, regional bar, risk donut, monthly trend |

---

## Data Model

### Fact tables

| Table | Description |
|-------|-------------|
| `fact_case` | Core case record — status, workflow stage, SLA, flags, financial values |
| `fact_case_stage_history` | Timestamp of each workflow stage transition per case |
| `fact_sar` | Suspicious Activity Reports filed from cases |
| `fact_alert` | Transaction monitoring / screening alerts (feeds cases) |
| `agg_daily_case_snapshot` | Pre-aggregated daily snapshot for fast dashboard queries |

### Dimension tables

| Table | Key Attributes |
|-------|---------------|
| `dim_region` | EMEA, APAC, AMER, LATAM |
| `dim_country` | 20 countries, ISO codes, FATF status, high-risk flag |
| `dim_entity` | 10 legal entities / branches |
| `dim_team` | 15 teams across 6 team types (AML, Sanctions, Fraud, KYC, FIU, Compliance) |
| `dim_analyst` | 120 analysts with grade and team assignment |
| `dim_financial_crime_type` | 18 crime types across 10 categories (ML, Sanctions, Fraud, TF, …) |
| `dim_risk_classification` | Low / Medium / High / Critical with SLA targets |
| `dim_priority` | P1–P4 with response SLAs in hours |
| `dim_case_source` | Transaction monitoring, sanctions screening, staff referral, regulatory, etc. |
| `dim_disposition` | 10 closure outcomes (SAR filed, LEA referral, no further action, etc.) |
| `dim_channel` | Retail, Corporate, Wealth, Trade Finance, Digital, Correspondent, IB, Insurance |

### Key computed columns (PostgreSQL generated)

```sql
actual_days_open  -- closed_date - opened_date (or today if open)
is_sla_breached   -- actual_days_open > sla_target_days
days_in_stage     -- seconds between stage_entered_at and stage_exited_at / 86400
```

---

## Virtual Datasets (SQL Lab)

Located in `superset/datasets/virtual_datasets.sql`. Each is a SELECT query registered as a Superset virtual dataset:

| Dataset | Used by |
|---------|---------|
| `vw_case_operational_summary` | Operational Overview, Crime Intelligence, Executive Summary |
| `vw_sla_performance` | SLA & Performance, Executive Summary |
| `vw_workflow_funnel` | Operational Overview (funnel chart) |
| `vw_case_volume_trend` | Time-series volume charts |
| `vw_team_workload` | Team & Analyst Workload |
| `vw_sar_intelligence` | Financial Exposure & Recovery |
| `vw_alert_to_case_conversion` | Crime Type Intelligence |
| `vw_financial_exposure` | Financial Exposure & Recovery |

---

## Self-service Dashboard Building for Analysts

Superset's Explore interface lets analysts build custom charts without SQL:

1. **Navigate to**: Charts → + Chart
2. **Select a dataset**: e.g. `vw_case_operational_summary`
3. **Choose a chart type**: Bar, Line, Pie, Table, World Map, Funnel, Heatmap, Scatter, Big Number, etc.
4. **Drag dimensions and metrics** from the left panel
5. **Add filters** (status, region, team, crime type, date range)
6. **Save** and add to a new or existing dashboard
7. **Set up cross-filters**: Dashboard → Edit → Enable cross-filtering
8. **Share**: Publish the dashboard to make it visible to other role groups

### Recommended starter charts for new analysts

| Chart idea | Dataset | Viz type |
|-----------|---------|----------|
| My team's open cases by stage | `vw_case_operational_summary` | Bar |
| SLA compliance heatmap (team × month) | `vw_sla_performance` | Heatmap |
| Caseload by crime category this week | `vw_case_operational_summary` | Pie / Donut |
| Country risk map | `vw_case_operational_summary` | World Map |
| Alert false positive trend | `vw_alert_to_case_conversion` | Line |
| Top cases by value at risk | `vw_financial_exposure` | Table |

---

## Dimensions for Slicing & Dicing

Analysts can filter any chart by any combination of:

**Organisational**
- Region (EMEA / APAC / AMER / LATAM)
- Country (20 countries, FATF status, high-risk flag)
- Legal Entity / Branch
- Team (15 teams × 6 types)
- Analyst grade

**Case attributes**
- Case status (Open / In Review / Escalated / Pending SAR / Closed / …)
- Workflow stage (Triage → Closure Approval → Closed — 10 stages)
- Risk level (Low / Medium / High / Critical)
- Priority (P1–P4)
- Crime category (10 categories)
- Crime type (18 specific typologies)
- Business channel (8 channels)
- Case source (10 sources)
- Closure disposition (10 outcomes)

**Flags**
- Involves PEP
- Involves sanctioned entity
- Cross-border
- Complex case
- Regulatory notified
- High-risk country

**Time**
- Date opened, closed, escalated
- SLA due date
- Month / quarter / year
- Age band (0-7 d / 8-14 d / 15-30 d / 31-60 d / 61-90 d / 90+ d)

**Financial**
- Estimated value at risk (USD)
- Confirmed loss (USD)
- Recovered (USD)
- Recovery rate %

---

## Roles & Access Control

| Role | Access level |
|------|-------------|
| `FCM_Analyst` | View dashboards, explore charts, run SQL against FCM DB |
| `FCM_TeamLead` | Above + create/edit charts and dashboards |
| `FCM_ComplianceManager` | Above + user management within their region |
| `FCM_FIU` | Full read access across all entities and regions |
| `admin` | Full Superset administration |

Row-level security (RLS) can be added in Superset to restrict `FCM_Analyst` users to their own team's cases. See **Security → Row Level Security Filters** in the admin panel.

---

## Customisation Guide

### Adding a new crime type
```sql
INSERT INTO dim_financial_crime_type
  (crime_type_code, crime_type_name, crime_category, regulatory_framework, is_sar_reportable)
VALUES ('NEW-CODE', 'New Crime Type', 'fraud', 'MLR2017', TRUE);
```

### Changing SLA targets
```sql
UPDATE dim_risk_classification SET sla_days = 45 WHERE risk_level = 'medium';
```

### Adding a new team / region / entity
Insert into the relevant `dim_*` table; all dashboards will automatically include the new dimension on next refresh.

### Adding a new virtual dataset
1. Write the SQL in SQL Lab → **Save As Dataset**
2. Build charts on top of it in Explore
3. Add charts to a dashboard

### Scheduling email reports
Navigate to **Settings → Alerts & Reports** — Superset's alert engine (via Celery Beat) is already configured.

---

## File Structure

```
superset_experiment/
├── docker-compose.yml                  # Full stack orchestration
├── db/
│   ├── 01_schema.sql                   # Full data model DDL
│   └── 02_seed_reference_data.sql      # Dimension table seed data
├── docker/
│   ├── postgres/
│   │   ├── init-multiple-dbs.sh        # Creates fcm_poc + superset databases
│   │   └── create-users.sql            # DB user creation
│   └── superset/
│       ├── superset_config.py          # Superset configuration
│       └── init_superset.sh            # Post-init: DB registration + roles
├── scripts/
│   ├── generate_sample_data.py         # Synthetic data generator (5k cases)
│   └── bootstrap_superset.py           # REST API: datasets + charts + dashboards
└── superset/
    ├── datasets/
    │   └── virtual_datasets.sql        # 8 saved SQL datasets
    └── dashboards/
        └── dashboard_spec.json         # Dashboard layout specification
```

---

## Production Considerations

| Concern | Recommendation |
|---------|---------------|
| Secret key | Generate with `openssl rand -base64 42` and set in env |
| HTTPS | Add a reverse proxy (nginx / Caddy) with TLS |
| Authentication | Configure LDAP/SAML in `superset_config.py` |
| Row-level security | Add RLS filters per team in Superset Admin |
| Database | Replace PostgreSQL with your enterprise DW (Snowflake, BigQuery, etc.) |
| Data refresh | Replace `agg_daily_case_snapshot` with a scheduled dbt/Airflow job |
| Case integration | Connect `fact_case` to your live case management API via CDC |
| Audit trail | Enable Superset audit logging + forward to SIEM |