-- =============================================================================
-- SUPERSET VIRTUAL DATASETS (saved SQL queries used as chart sources)
-- These are registered in Superset as "Virtual Datasets" pointing at the
-- FCM Case Management DB.  Paste each block into SQL Lab → Save As Dataset.
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
-- DATASET 1: vw_case_operational_summary
-- Purpose   : Drives the main Operational Overview dashboard.
--             One row per case with all key dimension labels resolved.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    fc.case_id,
    fc.case_reference,
    fc.opened_date,
    fc.closed_date,
    fc.review_due_date,
    fc.escalated_date,
    fc.case_status,
    fc.workflow_stage,
    fc.actual_days_open,
    fc.sla_target_days,
    fc.is_sla_breached,
    CASE WHEN fc.is_sla_breached THEN 'Breached' ELSE 'In SLA' END          AS sla_status_label,
    fc.estimated_value_usd,
    fc.confirmed_loss_usd,
    fc.recovered_usd,
    fc.involves_pep,
    fc.involves_sanctioned_entity,
    fc.cross_border,
    fc.is_complex,
    fc.sar_count,
    fc.law_enforcement_referrals,

    -- Crime type dimensions
    fct.crime_type_name,
    fct.crime_category,
    fct.regulatory_framework,
    fct.is_sar_reportable,

    -- Risk
    rc.risk_level,
    rc.sla_days                                                              AS risk_sla_days,

    -- Priority
    pr.priority_name,
    pr.response_hours,

    -- Source
    cs.source_name,
    cs.source_category,

    -- Channel
    ch.channel_name,

    -- Team
    t.team_name,
    t.team_type,

    -- Analyst
    a.display_name                                                           AS analyst_name,
    a.grade                                                                  AS analyst_grade,

    -- Entity / Geography
    e.entity_name,
    e.entity_type,
    co.country_name,
    co.country_code,
    co.is_high_risk                                                          AS is_high_risk_country,
    co.fatf_status,
    rg.region_name,
    rg.region_code,

    -- Disposition
    d.disposition_name,
    d.requires_sar,

    -- Age bands (useful for bar charts)
    CASE
        WHEN fc.actual_days_open <= 7  THEN '0-7 days'
        WHEN fc.actual_days_open <= 14 THEN '8-14 days'
        WHEN fc.actual_days_open <= 30 THEN '15-30 days'
        WHEN fc.actual_days_open <= 60 THEN '31-60 days'
        WHEN fc.actual_days_open <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END                                                                      AS age_band,

    -- Month/Year helpers for time-series filters
    DATE_TRUNC('month', fc.opened_date)                                      AS opened_month,
    DATE_TRUNC('week',  fc.opened_date)                                      AS opened_week,
    EXTRACT(YEAR  FROM fc.opened_date)::INT                                  AS opened_year,
    EXTRACT(MONTH FROM fc.opened_date)::INT                                  AS opened_month_num,
    TO_CHAR(fc.opened_date, 'Mon YYYY')                                      AS opened_month_label

FROM fact_case           fc
JOIN dim_financial_crime_type fct ON fct.crime_type_id  = fc.crime_type_id
JOIN dim_risk_classification  rc  ON rc.risk_class_id   = fc.risk_class_id
JOIN dim_priority             pr  ON pr.priority_id     = fc.priority_id
JOIN dim_case_source          cs  ON cs.source_id       = fc.source_id
JOIN dim_channel              ch  ON ch.channel_id      = fc.channel_id
JOIN dim_team                 t   ON t.team_id          = fc.team_id
JOIN dim_entity               e   ON e.entity_id        = fc.entity_id
JOIN dim_country              co  ON co.country_id      = fc.country_id
JOIN dim_region               rg  ON rg.region_id       = fc.region_id
LEFT JOIN dim_analyst         a   ON a.analyst_id       = fc.assigned_analyst_id
LEFT JOIN dim_disposition     d   ON d.disposition_id   = fc.disposition_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- DATASET 2: vw_sla_performance
-- Purpose   : SLA compliance by team, region, crime type, month.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    DATE_TRUNC('month', fc.opened_date)                     AS cohort_month,
    rg.region_name,
    t.team_name,
    t.team_type,
    fct.crime_category,
    fct.crime_type_name,
    rc.risk_level,
    co.country_name,
    fc.case_status,
    COUNT(*)                                                 AS total_cases,
    COUNT(*) FILTER (WHERE fc.case_status IN ('closed','withdrawn'))
                                                             AS closed_cases,
    COUNT(*) FILTER (WHERE fc.case_status IN ('closed','withdrawn')
                       AND NOT fc.is_sla_breached)           AS closed_in_sla,
    COUNT(*) FILTER (WHERE fc.case_status IN ('closed','withdrawn')
                       AND fc.is_sla_breached)               AS closed_sla_breached,
    COUNT(*) FILTER (WHERE fc.case_status NOT IN ('closed','withdrawn'))
                                                             AS open_cases,
    COUNT(*) FILTER (WHERE fc.case_status NOT IN ('closed','withdrawn')
                       AND fc.is_sla_breached)               AS open_sla_breached,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE NOT fc.is_sla_breached AND fc.case_status IN ('closed','withdrawn'))
              / NULLIF(COUNT(*) FILTER (WHERE fc.case_status IN ('closed','withdrawn')), 0)
    , 1)                                                     AS sla_compliance_pct,
    AVG(fc.actual_days_open)                                 AS avg_days_open,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fc.actual_days_open)
                                                             AS median_days_open,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY fc.actual_days_open)
                                                             AS p90_days_open,
    AVG(fc.sla_target_days)                                  AS avg_sla_target

FROM fact_case           fc
JOIN dim_financial_crime_type fct ON fct.crime_type_id = fc.crime_type_id
JOIN dim_risk_classification  rc  ON rc.risk_class_id  = fc.risk_class_id
JOIN dim_team                 t   ON t.team_id         = fc.team_id
JOIN dim_country              co  ON co.country_id     = fc.country_id
JOIN dim_region               rg  ON rg.region_id      = fc.region_id
GROUP BY 1,2,3,4,5,6,7,8,9;


-- ─────────────────────────────────────────────────────────────────────────────
-- DATASET 3: vw_workflow_funnel
-- Purpose   : Snapshot of current case counts at each workflow stage.
--             Drives pipeline / funnel charts.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    rg.region_name,
    t.team_name,
    t.team_type,
    fct.crime_category,
    rc.risk_level,
    co.country_name,
    fc.workflow_stage,
    CASE fc.workflow_stage
        WHEN 'triage'                 THEN 1
        WHEN 'initial_review'         THEN 2
        WHEN 'investigation'          THEN 3
        WHEN 'enhanced_due_diligence' THEN 4
        WHEN 'quality_assurance'      THEN 5
        WHEN 'senior_review'          THEN 6
        WHEN 'legal_review'           THEN 7
        WHEN 'regulatory_reporting'   THEN 8
        WHEN 'closure_approval'       THEN 9
        WHEN 'closed'                 THEN 10
        ELSE 99
    END                                                      AS stage_order,
    COUNT(*)                                                 AS case_count,
    SUM(fc.estimated_value_usd)                              AS total_value_at_risk,
    AVG(fc.actual_days_open)                                 AS avg_age_days,
    COUNT(*) FILTER (WHERE fc.is_sla_breached)               AS sla_breached_count

FROM fact_case           fc
JOIN dim_financial_crime_type fct ON fct.crime_type_id = fc.crime_type_id
JOIN dim_risk_classification  rc  ON rc.risk_class_id  = fc.risk_class_id
JOIN dim_team                 t   ON t.team_id         = fc.team_id
JOIN dim_country              co  ON co.country_id     = fc.country_id
JOIN dim_region               rg  ON rg.region_id      = fc.region_id
WHERE fc.case_status NOT IN ('closed','withdrawn')
GROUP BY 1,2,3,4,5,6,7,8;


-- ─────────────────────────────────────────────────────────────────────────────
-- DATASET 4: vw_case_volume_trend
-- Purpose   : Daily / weekly / monthly case volumes opened and closed.
--             Drives time-series line and bar charts.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    gs::DATE                                                 AS report_date,
    rg.region_name,
    t.team_name,
    fct.crime_category,
    COALESCE(COUNT(fc.case_id) FILTER (WHERE fc.opened_date = gs::DATE), 0)
                                                             AS cases_opened,
    COALESCE(COUNT(fc.case_id) FILTER (WHERE fc.closed_date = gs::DATE), 0)
                                                             AS cases_closed,
    COALESCE(COUNT(fc.case_id) FILTER (
        WHERE fc.opened_date <= gs::DATE
          AND (fc.closed_date IS NULL OR fc.closed_date > gs::DATE)
    ), 0)                                                    AS cases_open_at_eod,
    COALESCE(COUNT(fc.case_id) FILTER (
        WHERE fc.escalated_date = gs::DATE
    ), 0)                                                    AS cases_escalated

FROM generate_series('2024-01-01'::DATE, CURRENT_DATE, '1 day') gs
CROSS JOIN dim_region   rg
CROSS JOIN dim_team     t
CROSS JOIN dim_financial_crime_type fct
LEFT JOIN fact_case fc
    ON  (fc.opened_date  = gs::DATE OR
         fc.closed_date  = gs::DATE OR
         fc.escalated_date = gs::DATE OR
         (fc.opened_date <= gs::DATE AND (fc.closed_date IS NULL OR fc.closed_date > gs::DATE)))
    AND fc.region_id      = rg.region_id
    AND fc.team_id        = t.team_id
    AND fc.crime_type_id  = fct.crime_type_id
GROUP BY 1,2,3,4;


-- ─────────────────────────────────────────────────────────────────────────────
-- DATASET 5: vw_team_workload
-- Purpose   : Analyst-level and team-level workload metrics.
--             Drives capacity / heatmap charts.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    t.team_code,
    t.team_name,
    t.team_type,
    t.headcount,
    rg.region_name,
    a.display_name                                           AS analyst_name,
    a.analyst_code,
    a.grade,
    COUNT(fc.case_id) FILTER (WHERE fc.case_status NOT IN ('closed','withdrawn'))
                                                             AS open_cases,
    COUNT(fc.case_id) FILTER (WHERE fc.case_status = 'escalated')
                                                             AS escalated_cases,
    COUNT(fc.case_id) FILTER (WHERE fc.is_sla_breached
                                AND fc.case_status NOT IN ('closed','withdrawn'))
                                                             AS sla_breached_open,
    COUNT(fc.case_id) FILTER (WHERE fc.case_status = 'pending_information')
                                                             AS pending_info_cases,
    ROUND(AVG(fc.actual_days_open) FILTER (
        WHERE fc.case_status NOT IN ('closed','withdrawn')), 1)
                                                             AS avg_open_case_age,
    COUNT(fc.case_id) FILTER (WHERE rc.risk_level = 'critical'
                                AND fc.case_status NOT IN ('closed','withdrawn'))
                                                             AS critical_open_cases,
    ROUND(
        COUNT(fc.case_id) FILTER (WHERE fc.case_status NOT IN ('closed','withdrawn'))::NUMERIC
        / NULLIF(t.headcount, 0)
    , 1)                                                     AS cases_per_fte

FROM dim_team            t
JOIN dim_region          rg ON rg.region_id   = t.region_id
JOIN dim_analyst         a  ON a.team_id      = t.team_id AND a.is_active
LEFT JOIN fact_case      fc ON fc.assigned_analyst_id = a.analyst_id
LEFT JOIN dim_risk_classification rc ON rc.risk_class_id = fc.risk_class_id
GROUP BY t.team_code, t.team_name, t.team_type, t.headcount,
         rg.region_name, a.display_name, a.analyst_code, a.grade;


-- ─────────────────────────────────────────────────────────────────────────────
-- DATASET 6: vw_sar_intelligence
-- Purpose   : SAR / regulatory reporting analytics.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    s.sar_reference,
    s.filed_date,
    DATE_TRUNC('month', s.filed_date)                        AS filed_month,
    s.reporting_authority,
    s.sar_type,
    s.sar_status,
    s.consent_requested,
    s.consent_granted,
    fct.crime_type_name,
    fct.crime_category,
    t.team_name,
    t.team_type,
    rg.region_name,
    co.country_name,
    e.entity_name,
    fc.case_reference,
    labels.risk_level_label,
    labels.priority_name_label

FROM fact_sar s
JOIN fact_case              fc  ON fc.case_id      = s.case_id
JOIN dim_financial_crime_type fct ON fct.crime_type_id = s.crime_type_id
JOIN dim_team               t   ON t.team_id       = s.team_id
JOIN dim_country            co  ON co.country_id   = s.country_id
JOIN dim_region             rg  ON rg.region_id    = t.region_id
JOIN dim_entity             e   ON e.entity_id     = s.entity_id
-- self-join via subquery to pull labels
JOIN (
    SELECT fc2.case_id,
           rc.risk_level  AS risk_level_label,
           pr.priority_name AS priority_name_label
    FROM fact_case fc2
    JOIN dim_risk_classification rc ON rc.risk_class_id = fc2.risk_class_id
    JOIN dim_priority pr             ON pr.priority_id  = fc2.priority_id
) labels ON labels.case_id = fc.case_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- DATASET 7: vw_alert_to_case_conversion
-- Purpose   : Alert effectiveness - conversion rate, false positive rate,
--             mean time to review. Helps justify tooling investment.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    DATE_TRUNC('month', a.alert_generated_at)                AS alert_month,
    rg.region_name,
    ch.channel_name,
    a.alert_type,
    fct.crime_category,
    COUNT(a.alert_id)                                        AS total_alerts,
    COUNT(a.alert_id) FILTER (WHERE a.alert_status = 'closed_false_positive')
                                                             AS false_positives,
    COUNT(a.alert_id) FILTER (WHERE a.alert_status = 'closed_true_positive')
                                                             AS true_positives,
    COUNT(a.alert_id) FILTER (WHERE a.case_id IS NOT NULL)   AS escalated_to_case,
    ROUND(100.0 * COUNT(a.alert_id) FILTER (WHERE a.alert_status = 'closed_false_positive')
          / NULLIF(COUNT(a.alert_id), 0), 1)                 AS false_positive_rate_pct,
    ROUND(100.0 * COUNT(a.alert_id) FILTER (WHERE a.case_id IS NOT NULL)
          / NULLIF(COUNT(a.alert_id), 0), 1)                 AS case_conversion_rate_pct,
    ROUND(AVG(a.resolution_minutes)::NUMERIC, 0)             AS avg_resolution_minutes,
    ROUND(AVG(a.alert_score)::NUMERIC, 1)                    AS avg_alert_score,
    SUM(a.transaction_amount_usd)                            AS total_transaction_volume

FROM fact_alert          a
JOIN dim_entity          e   ON e.entity_id   = a.entity_id
JOIN dim_country         co  ON co.country_id = a.country_id
JOIN dim_region          rg  ON rg.region_id  = e.region_id
JOIN dim_channel         ch  ON ch.channel_id = a.channel_id
LEFT JOIN dim_financial_crime_type fct ON fct.crime_type_id = a.crime_type_id
GROUP BY 1,2,3,4,5;


-- ─────────────────────────────────────────────────────────────────────────────
-- DATASET 8: vw_financial_exposure
-- Purpose   : Value-at-risk, confirmed losses and recovery rates.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    DATE_TRUNC('quarter', fc.opened_date)                    AS opened_quarter,
    rg.region_name,
    co.country_name,
    fct.crime_category,
    fct.crime_type_name,
    rc.risk_level,
    ch.channel_name,
    e.entity_name,
    COUNT(fc.case_id)                                        AS case_count,
    SUM(fc.estimated_value_usd)                              AS total_estimated_usd,
    SUM(fc.confirmed_loss_usd)                               AS total_confirmed_loss_usd,
    SUM(fc.recovered_usd)                                    AS total_recovered_usd,
    ROUND(100.0 * SUM(fc.recovered_usd)
          / NULLIF(SUM(fc.confirmed_loss_usd), 0), 1)        AS recovery_rate_pct,
    AVG(fc.estimated_value_usd)                              AS avg_case_value_usd,
    MAX(fc.estimated_value_usd)                              AS max_case_value_usd

FROM fact_case           fc
JOIN dim_financial_crime_type fct ON fct.crime_type_id = fc.crime_type_id
JOIN dim_risk_classification  rc  ON rc.risk_class_id  = fc.risk_class_id
JOIN dim_channel              ch  ON ch.channel_id     = fc.channel_id
JOIN dim_entity               e   ON e.entity_id       = fc.entity_id
JOIN dim_country              co  ON co.country_id     = fc.country_id
JOIN dim_region               rg  ON rg.region_id      = fc.region_id
WHERE fc.estimated_value_usd IS NOT NULL
GROUP BY 1,2,3,4,5,6,7,8;
