-- ============================================================
-- Financial Crime Case Management – Schema
-- Multi-region / multi-market data model
-- ============================================================

-- Reference: regions and markets
CREATE TABLE IF NOT EXISTS dim_region (
    region_id   SERIAL PRIMARY KEY,
    region_code VARCHAR(10)  NOT NULL UNIQUE,
    region_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_market (
    market_id   SERIAL PRIMARY KEY,
    market_code VARCHAR(10)  NOT NULL UNIQUE,
    market_name VARCHAR(100) NOT NULL,
    region_id   INT NOT NULL REFERENCES dim_region(region_id),
    currency    VARCHAR(3)   NOT NULL
);

-- Reference: case categories and types
CREATE TABLE IF NOT EXISTS dim_case_type (
    case_type_id   SERIAL PRIMARY KEY,
    case_type_code VARCHAR(30) NOT NULL UNIQUE,
    case_type_name VARCHAR(100) NOT NULL,
    category       VARCHAR(50) NOT NULL   -- e.g. AML, Fraud, Sanctions
);

-- Reference: investigators / analysts
CREATE TABLE IF NOT EXISTS dim_analyst (
    analyst_id   SERIAL PRIMARY KEY,
    analyst_code VARCHAR(20)  NOT NULL UNIQUE,
    full_name    VARCHAR(100) NOT NULL,
    team         VARCHAR(50)  NOT NULL,
    market_id    INT NOT NULL REFERENCES dim_market(market_id),
    is_active    BOOLEAN NOT NULL DEFAULT TRUE
);

-- Core: cases
CREATE TABLE IF NOT EXISTS fact_case (
    case_id          SERIAL PRIMARY KEY,
    case_reference   VARCHAR(30) NOT NULL UNIQUE,
    case_type_id     INT NOT NULL REFERENCES dim_case_type(case_type_id),
    market_id        INT NOT NULL REFERENCES dim_market(market_id),
    status           VARCHAR(20) NOT NULL,  -- Open, In Review, Escalated, Closed - SAR Filed, Closed - No Action
    priority         VARCHAR(10) NOT NULL,  -- Low, Medium, High, Critical
    risk_score       NUMERIC(5,2),
    assigned_analyst INT REFERENCES dim_analyst(analyst_id),
    opened_date      DATE NOT NULL,
    last_updated     TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_date      DATE,
    closure_reason   VARCHAR(50),           -- SAR Filed, No Action, Referred, False Positive
    is_sar_filed     BOOLEAN NOT NULL DEFAULT FALSE,
    is_regulatory_report BOOLEAN NOT NULL DEFAULT FALSE,
    notes            TEXT
);

-- Subjects linked to a case (individuals or legal entities)
CREATE TABLE IF NOT EXISTS fact_subject (
    subject_id       SERIAL PRIMARY KEY,
    case_id          INT NOT NULL REFERENCES fact_case(case_id),
    subject_type     VARCHAR(20) NOT NULL,  -- Individual, Corporate, Government
    full_name        VARCHAR(150),
    date_of_birth    DATE,
    nationality      VARCHAR(3),            -- ISO-3166-1 alpha-3
    country_of_res   VARCHAR(3),
    id_type          VARCHAR(30),
    id_number        VARCHAR(50),
    risk_rating      VARCHAR(10),           -- Low, Medium, High, PEP, Sanctioned
    is_pep           BOOLEAN NOT NULL DEFAULT FALSE,
    is_sanctioned    BOOLEAN NOT NULL DEFAULT FALSE
);

-- Alerts that triggered or are linked to a case
CREATE TABLE IF NOT EXISTS fact_alert (
    alert_id         SERIAL PRIMARY KEY,
    case_id          INT REFERENCES fact_case(case_id),
    alert_reference  VARCHAR(30) NOT NULL UNIQUE,
    alert_type       VARCHAR(50) NOT NULL,  -- Structuring, High Value, Unusual Pattern, Sanctions Hit, PEP Activity
    alert_date       DATE NOT NULL,
    alert_source     VARCHAR(50),           -- Transaction Monitoring, Screening, Manual, Tip-off
    amount           NUMERIC(18,2),
    currency         VARCHAR(3),
    market_id        INT NOT NULL REFERENCES dim_market(market_id),
    status           VARCHAR(20) NOT NULL DEFAULT 'Pending', -- Pending, Assigned, Closed
    disposition      VARCHAR(30)            -- True Positive, False Positive, Escalated
);

-- Transactions associated with a case
CREATE TABLE IF NOT EXISTS fact_transaction (
    txn_id           SERIAL PRIMARY KEY,
    case_id          INT NOT NULL REFERENCES fact_case(case_id),
    txn_reference    VARCHAR(40) NOT NULL UNIQUE,
    txn_date         DATE NOT NULL,
    txn_type         VARCHAR(30) NOT NULL,  -- Wire, SWIFT, Cash, Card, Crypto, Internal
    amount           NUMERIC(18,2) NOT NULL,
    amount_usd       NUMERIC(18,2),         -- normalised to USD
    currency         VARCHAR(3) NOT NULL,
    from_account     VARCHAR(40),
    from_institution VARCHAR(100),
    from_country     VARCHAR(3),
    to_account       VARCHAR(40),
    to_institution   VARCHAR(100),
    to_country       VARCHAR(3),
    channel          VARCHAR(30),           -- Online, Branch, ATM, Mobile, Correspondent
    is_suspicious    BOOLEAN NOT NULL DEFAULT FALSE
);

-- Investigation activity log
CREATE TABLE IF NOT EXISTS fact_investigation_action (
    action_id        SERIAL PRIMARY KEY,
    case_id          INT NOT NULL REFERENCES fact_case(case_id),
    analyst_id       INT NOT NULL REFERENCES dim_analyst(analyst_id),
    action_date      TIMESTAMP NOT NULL DEFAULT NOW(),
    action_type      VARCHAR(50) NOT NULL,  -- Review, Interview, Document Request, Escalation, SAR Draft, Closure
    action_detail    TEXT,
    outcome          VARCHAR(50)
);

-- ============================================================
-- Useful views for Superset dashboards
-- ============================================================

CREATE OR REPLACE VIEW vw_case_summary AS
SELECT
    fc.case_id,
    fc.case_reference,
    ct.category            AS case_category,
    ct.case_type_name      AS case_type,
    fc.status,
    fc.priority,
    fc.risk_score,
    fc.opened_date,
    fc.closed_date,
    CASE WHEN fc.closed_date IS NOT NULL
         THEN fc.closed_date - fc.opened_date
    END                    AS days_to_close,
    fc.is_sar_filed,
    fc.is_regulatory_report,
    fc.closure_reason,
    dm.market_code,
    dm.market_name,
    dm.currency            AS market_currency,
    dr.region_code,
    dr.region_name,
    da.full_name           AS analyst_name,
    da.team                AS analyst_team
FROM fact_case fc
JOIN dim_case_type ct ON ct.case_type_id = fc.case_type_id
JOIN dim_market    dm ON dm.market_id    = fc.market_id
JOIN dim_region    dr ON dr.region_id    = dm.region_id
LEFT JOIN dim_analyst da ON da.analyst_id = fc.assigned_analyst;

CREATE OR REPLACE VIEW vw_alert_summary AS
SELECT
    fa.alert_id,
    fa.alert_reference,
    fa.alert_type,
    fa.alert_date,
    fa.alert_source,
    fa.amount,
    fa.currency,
    fa.status             AS alert_status,
    fa.disposition,
    fc.case_reference,
    fc.status             AS case_status,
    ct.category           AS case_category,
    dm.market_name,
    dr.region_name
FROM fact_alert fa
LEFT JOIN fact_case     fc ON fc.case_id     = fa.case_id
LEFT JOIN dim_case_type ct ON ct.case_type_id = fc.case_type_id
JOIN  dim_market        dm ON dm.market_id   = fa.market_id
JOIN  dim_region        dr ON dr.region_id   = dm.region_id;

CREATE OR REPLACE VIEW vw_transaction_summary AS
SELECT
    ft.txn_id,
    ft.txn_reference,
    ft.txn_date,
    ft.txn_type,
    ft.amount,
    ft.amount_usd,
    ft.currency,
    ft.from_country,
    ft.to_country,
    ft.channel,
    ft.is_suspicious,
    fc.case_reference,
    fc.status             AS case_status,
    ct.category           AS case_category,
    dm.market_name,
    dr.region_name
FROM fact_transaction ft
JOIN fact_case     fc ON fc.case_id     = ft.case_id
JOIN dim_case_type ct ON ct.case_type_id = fc.case_type_id
JOIN dim_market    dm ON dm.market_id    = fc.market_id
JOIN dim_region    dr ON dr.region_id    = dm.region_id;

CREATE OR REPLACE VIEW vw_monthly_case_volume AS
SELECT
    DATE_TRUNC('month', opened_date)::DATE AS month,
    dr.region_name,
    dm.market_name,
    ct.category   AS case_category,
    fc.status,
    fc.priority,
    COUNT(*)      AS case_count,
    SUM(CASE WHEN fc.is_sar_filed THEN 1 ELSE 0 END) AS sar_count
FROM fact_case fc
JOIN dim_case_type ct ON ct.case_type_id = fc.case_type_id
JOIN dim_market    dm ON dm.market_id    = fc.market_id
JOIN dim_region    dr ON dr.region_id    = dm.region_id
GROUP BY 1,2,3,4,5,6;

CREATE OR REPLACE VIEW vw_analyst_workload AS
SELECT
    da.full_name,
    da.team,
    dm.market_name,
    dr.region_name,
    fc.status,
    fc.priority,
    COUNT(*) AS case_count,
    AVG(fc.risk_score) AS avg_risk_score
FROM fact_case fc
JOIN dim_analyst da ON da.analyst_id = fc.assigned_analyst
JOIN dim_market  dm ON dm.market_id  = fc.market_id
JOIN dim_region  dr ON dr.region_id  = dm.region_id
GROUP BY 1,2,3,4,5,6;
