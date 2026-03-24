-- =============================================================================
-- Financial Crime Case Management System - Database Schema
-- Multi-regional, multi-national bank POC for Apache Superset dashboarding
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- REFERENCE / DIMENSION TABLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE dim_region (
    region_id       SERIAL PRIMARY KEY,
    region_code     VARCHAR(10)  NOT NULL UNIQUE,
    region_name     VARCHAR(100) NOT NULL,
    timezone        VARCHAR(50)  NOT NULL
);

CREATE TABLE dim_country (
    country_id      SERIAL PRIMARY KEY,
    country_code    CHAR(3)      NOT NULL UNIQUE,   -- ISO 3166-1 alpha-3
    country_name    VARCHAR(100) NOT NULL,
    region_id       INT          NOT NULL REFERENCES dim_region(region_id),
    is_high_risk    BOOLEAN      NOT NULL DEFAULT FALSE,
    fatf_status     VARCHAR(30)  NOT NULL DEFAULT 'compliant'
                        CHECK (fatf_status IN ('compliant','grey_list','black_list'))
);

CREATE TABLE dim_entity (
    entity_id       SERIAL PRIMARY KEY,
    entity_code     VARCHAR(20)  NOT NULL UNIQUE,
    entity_name     VARCHAR(200) NOT NULL,
    entity_type     VARCHAR(30)  NOT NULL
                        CHECK (entity_type IN ('legal_entity','branch','subsidiary','jv')),
    country_id      INT          NOT NULL REFERENCES dim_country(country_id),
    region_id       INT          NOT NULL REFERENCES dim_region(region_id)
);

CREATE TABLE dim_team (
    team_id         SERIAL PRIMARY KEY,
    team_code       VARCHAR(20)  NOT NULL UNIQUE,
    team_name       VARCHAR(100) NOT NULL,
    team_type       VARCHAR(30)  NOT NULL
                        CHECK (team_type IN (
                            'aml_investigations',
                            'sanctions_screening',
                            'fraud_operations',
                            'kyc_remediation',
                            'compliance_advisory',
                            'financial_intelligence'
                        )),
    region_id       INT          NOT NULL REFERENCES dim_region(region_id),
    entity_id       INT          REFERENCES dim_entity(entity_id),
    manager_name    VARCHAR(100),
    headcount       INT
);

CREATE TABLE dim_financial_crime_type (
    crime_type_id   SERIAL PRIMARY KEY,
    crime_type_code VARCHAR(30)  NOT NULL UNIQUE,
    crime_type_name VARCHAR(100) NOT NULL,
    crime_category  VARCHAR(50)  NOT NULL
                        CHECK (crime_category IN (
                            'money_laundering',
                            'sanctions_evasion',
                            'fraud',
                            'bribery_corruption',
                            'terrorist_financing',
                            'tax_evasion',
                            'market_abuse',
                            'cybercrime',
                            'human_trafficking',
                            'proliferation_financing'
                        )),
    regulatory_framework VARCHAR(50),  -- e.g. 'POCA','TACT','MLR2017','OFAC','EU_AMLD6'
    is_sar_reportable BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE dim_risk_classification (
    risk_class_id   SERIAL PRIMARY KEY,
    risk_level      VARCHAR(20)  NOT NULL UNIQUE
                        CHECK (risk_level IN ('low','medium','high','critical')),
    risk_score_min  INT NOT NULL,
    risk_score_max  INT NOT NULL,
    sla_days        INT NOT NULL,   -- target calendar days to close
    escalation_days INT NOT NULL    -- days before mandatory escalation
);

CREATE TABLE dim_priority (
    priority_id     SERIAL PRIMARY KEY,
    priority_name   VARCHAR(20)  NOT NULL UNIQUE
                        CHECK (priority_name IN ('P1','P2','P3','P4')),
    description     VARCHAR(200),
    response_hours  INT NOT NULL   -- initial response SLA in hours
);

CREATE TABLE dim_case_source (
    source_id       SERIAL PRIMARY KEY,
    source_code     VARCHAR(30)  NOT NULL UNIQUE,
    source_name     VARCHAR(100) NOT NULL,
    source_category VARCHAR(40)  NOT NULL
                        CHECK (source_category IN (
                            'automated_alert',
                            'human_referral',
                            'regulatory',
                            'law_enforcement',
                            'internal_audit',
                            'customer_disclosure',
                            'transaction_monitoring'
                        ))
);

CREATE TABLE dim_disposition (
    disposition_id  SERIAL PRIMARY KEY,
    disposition_code VARCHAR(30) NOT NULL UNIQUE,
    disposition_name VARCHAR(100) NOT NULL,
    requires_sar     BOOLEAN NOT NULL DEFAULT FALSE,
    requires_restraint BOOLEAN NOT NULL DEFAULT FALSE,
    is_closed        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE dim_channel (
    channel_id      SERIAL PRIMARY KEY,
    channel_code    VARCHAR(20)  NOT NULL UNIQUE,
    channel_name    VARCHAR(50)  NOT NULL
                        CHECK (channel_name IN (
                            'retail_banking',
                            'corporate_banking',
                            'wealth_management',
                            'trade_finance',
                            'digital_banking',
                            'correspondent_banking',
                            'investment_banking',
                            'insurance'
                        ))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- ANALYST / CASE WORKER (anonymised for POC)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE dim_analyst (
    analyst_id      SERIAL PRIMARY KEY,
    analyst_code    VARCHAR(20)  NOT NULL UNIQUE,
    display_name    VARCHAR(100) NOT NULL,
    grade           VARCHAR(20),
    team_id         INT          NOT NULL REFERENCES dim_team(team_id),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- CORE FACT TABLE: CASES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE fact_case (
    case_id             SERIAL PRIMARY KEY,
    case_reference      VARCHAR(30)  NOT NULL UNIQUE,  -- e.g. FCM-2025-0001234
    case_title          VARCHAR(200),
    crime_type_id       INT NOT NULL REFERENCES dim_financial_crime_type(crime_type_id),
    risk_class_id       INT NOT NULL REFERENCES dim_risk_classification(risk_class_id),
    priority_id         INT NOT NULL REFERENCES dim_priority(priority_id),
    source_id           INT NOT NULL REFERENCES dim_case_source(source_id),
    channel_id          INT NOT NULL REFERENCES dim_channel(channel_id),
    entity_id           INT NOT NULL REFERENCES dim_entity(entity_id),
    country_id          INT NOT NULL REFERENCES dim_country(country_id),
    region_id           INT NOT NULL REFERENCES dim_region(region_id),
    team_id             INT NOT NULL REFERENCES dim_team(team_id),
    assigned_analyst_id INT          REFERENCES dim_analyst(analyst_id),

    -- Lifecycle dates
    opened_date         DATE NOT NULL,
    assigned_date       DATE,
    first_action_date   DATE,
    review_due_date     DATE NOT NULL,  -- calculated from SLA
    escalated_date      DATE,
    closed_date         DATE,

    -- Status & workflow
    case_status         VARCHAR(30) NOT NULL DEFAULT 'open'
                            CHECK (case_status IN (
                                'open',
                                'in_review',
                                'pending_information',
                                'escalated',
                                'pending_sar',
                                'pending_closure',
                                'closed',
                                'withdrawn'
                            )),
    workflow_stage      VARCHAR(50) NOT NULL DEFAULT 'triage'
                            CHECK (workflow_stage IN (
                                'triage',
                                'initial_review',
                                'investigation',
                                'enhanced_due_diligence',
                                'quality_assurance',
                                'senior_review',
                                'legal_review',
                                'regulatory_reporting',
                                'closure_approval',
                                'closed'
                            )),
    disposition_id      INT REFERENCES dim_disposition(disposition_id),

    -- SLA tracking
    sla_target_days     INT NOT NULL,
    actual_days_open    INT,          -- computed at insert/update time
    is_sla_breached     BOOLEAN NOT NULL DEFAULT FALSE,

    -- Financial values
    estimated_value_usd NUMERIC(20,2),
    confirmed_loss_usd  NUMERIC(20,2),
    recovered_usd       NUMERIC(20,2),

    -- Counters
    sar_count           INT NOT NULL DEFAULT 0,
    law_enforcement_referrals INT NOT NULL DEFAULT 0,
    linked_case_count   INT NOT NULL DEFAULT 0,

    -- Flags
    involves_pep        BOOLEAN NOT NULL DEFAULT FALSE,
    involves_sanctioned_entity BOOLEAN NOT NULL DEFAULT FALSE,
    cross_border        BOOLEAN NOT NULL DEFAULT FALSE,
    is_complex          BOOLEAN NOT NULL DEFAULT FALSE,
    regulatory_notified BOOLEAN NOT NULL DEFAULT FALSE,

    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- CASE TIMELINE / STAGE HISTORY (for workflow funnel analysis)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE fact_case_stage_history (
    stage_history_id    SERIAL PRIMARY KEY,
    case_id             INT          NOT NULL REFERENCES fact_case(case_id),
    workflow_stage      VARCHAR(50)  NOT NULL,
    stage_entered_at    TIMESTAMPTZ  NOT NULL,
    stage_exited_at     TIMESTAMPTZ,
    days_in_stage       NUMERIC(10,2),   -- computed at insert/update time
    actor_analyst_id    INT          REFERENCES dim_analyst(analyst_id),
    notes               TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- SARs (Suspicious Activity Reports)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE fact_sar (
    sar_id              SERIAL PRIMARY KEY,
    sar_reference       VARCHAR(30)  NOT NULL UNIQUE,
    case_id             INT          NOT NULL REFERENCES fact_case(case_id),
    entity_id           INT          NOT NULL REFERENCES dim_entity(entity_id),
    country_id          INT          NOT NULL REFERENCES dim_country(country_id),
    team_id             INT          NOT NULL REFERENCES dim_team(team_id),
    analyst_id          INT          NOT NULL REFERENCES dim_analyst(analyst_id),
    filed_date          DATE         NOT NULL,
    reporting_authority VARCHAR(100) NOT NULL,   -- e.g. NCA, FinCEN, AUSTRAC
    sar_type            VARCHAR(40)  NOT NULL
                            CHECK (sar_type IN ('initial','addendum','defence_against_money_laundering')),
    sar_status          VARCHAR(20)  NOT NULL DEFAULT 'filed'
                            CHECK (sar_status IN ('draft','filed','acknowledged','queried','closed')),
    consent_requested   BOOLEAN      NOT NULL DEFAULT FALSE,
    consent_granted     BOOLEAN,
    crime_type_id       INT          NOT NULL REFERENCES dim_financial_crime_type(crime_type_id),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- ALERTS (from transaction monitoring / screening - feeding cases)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE fact_alert (
    alert_id            SERIAL PRIMARY KEY,
    alert_reference     VARCHAR(30)  NOT NULL UNIQUE,
    case_id             INT          REFERENCES fact_case(case_id),  -- NULL = not yet linked
    alert_type          VARCHAR(40)  NOT NULL
                            CHECK (alert_type IN (
                                'transaction_monitoring',
                                'sanctions_hit',
                                'pep_match',
                                'adverse_media',
                                'unusual_behaviour',
                                'fraud_indicator',
                                'kyc_expiry'
                            )),
    alert_score         INT,
    alert_status        VARCHAR(30)  NOT NULL DEFAULT 'open'
                            CHECK (alert_status IN ('open','in_review','escalated','closed_false_positive','closed_true_positive','merged')),
    entity_id           INT          NOT NULL REFERENCES dim_entity(entity_id),
    country_id          INT          NOT NULL REFERENCES dim_country(country_id),
    channel_id          INT          NOT NULL REFERENCES dim_channel(channel_id),
    crime_type_id       INT          REFERENCES dim_financial_crime_type(crime_type_id),
    transaction_amount_usd NUMERIC(20,2),
    alert_generated_at  TIMESTAMPTZ  NOT NULL,
    reviewed_at         TIMESTAMPTZ,
    resolution_minutes  INT,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- AGGREGATE DAILY SNAPSHOT (pre-aggregated for fast Superset queries)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE agg_daily_case_snapshot (
    snapshot_id         SERIAL PRIMARY KEY,
    snapshot_date       DATE         NOT NULL,
    region_id           INT          NOT NULL REFERENCES dim_region(region_id),
    country_id          INT          NOT NULL REFERENCES dim_country(country_id),
    entity_id           INT          NOT NULL REFERENCES dim_entity(entity_id),
    team_id             INT          NOT NULL REFERENCES dim_team(team_id),
    crime_type_id       INT          NOT NULL REFERENCES dim_financial_crime_type(crime_type_id),
    risk_class_id       INT          NOT NULL REFERENCES dim_risk_classification(risk_class_id),

    -- Counts
    cases_open          INT NOT NULL DEFAULT 0,
    cases_opened_today  INT NOT NULL DEFAULT 0,
    cases_closed_today  INT NOT NULL DEFAULT 0,
    cases_escalated     INT NOT NULL DEFAULT 0,
    cases_in_sla        INT NOT NULL DEFAULT 0,
    cases_sla_breached  INT NOT NULL DEFAULT 0,
    cases_pending_info  INT NOT NULL DEFAULT 0,
    cases_pending_sar   INT NOT NULL DEFAULT 0,

    -- Workflow stage breakdown
    cases_triage        INT NOT NULL DEFAULT 0,
    cases_initial_review INT NOT NULL DEFAULT 0,
    cases_investigation INT NOT NULL DEFAULT 0,
    cases_edd           INT NOT NULL DEFAULT 0,
    cases_qa            INT NOT NULL DEFAULT 0,
    cases_senior_review INT NOT NULL DEFAULT 0,
    cases_legal_review  INT NOT NULL DEFAULT 0,
    cases_reg_reporting INT NOT NULL DEFAULT 0,
    cases_closure_approval INT NOT NULL DEFAULT 0,

    -- Financial
    total_value_at_risk_usd   NUMERIC(20,2) NOT NULL DEFAULT 0,
    total_confirmed_loss_usd  NUMERIC(20,2) NOT NULL DEFAULT 0,
    total_recovered_usd       NUMERIC(20,2) NOT NULL DEFAULT 0,

    -- SARs & referrals
    sars_filed          INT NOT NULL DEFAULT 0,
    law_enforcement_referrals INT NOT NULL DEFAULT 0,

    -- Avg age
    avg_case_age_days   NUMERIC(10,2),
    p90_case_age_days   NUMERIC(10,2),

    UNIQUE (snapshot_date, region_id, country_id, entity_id, team_id, crime_type_id, risk_class_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES for Superset query performance
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX idx_fact_case_status         ON fact_case(case_status);
CREATE INDEX idx_fact_case_region         ON fact_case(region_id);
CREATE INDEX idx_fact_case_country        ON fact_case(country_id);
CREATE INDEX idx_fact_case_team           ON fact_case(team_id);
CREATE INDEX idx_fact_case_crime_type     ON fact_case(crime_type_id);
CREATE INDEX idx_fact_case_risk_class     ON fact_case(risk_class_id);
CREATE INDEX idx_fact_case_opened_date    ON fact_case(opened_date);
CREATE INDEX idx_fact_case_closed_date    ON fact_case(closed_date);
CREATE INDEX idx_fact_case_sla_breached   ON fact_case(is_sla_breached);
CREATE INDEX idx_fact_case_workflow_stage ON fact_case(workflow_stage);
CREATE INDEX idx_agg_snapshot_date        ON agg_daily_case_snapshot(snapshot_date);
CREATE INDEX idx_agg_snapshot_region      ON agg_daily_case_snapshot(region_id);
CREATE INDEX idx_agg_snapshot_team        ON agg_daily_case_snapshot(team_id);
