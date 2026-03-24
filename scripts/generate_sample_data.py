#!/usr/bin/env python3
"""
Financial Crime Case Management System - Sample Data Generator
Generates realistic synthetic data for the POC database.
Run: python generate_sample_data.py
"""

import os
import random
import string
import sys
from datetime import date, timedelta
from decimal import Decimal

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    print("Install psycopg2:  pip install psycopg2-binary")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.environ.get("FCM_DB_HOST", "localhost"),
    "port":     int(os.environ.get("FCM_DB_PORT", 5432)),
    "dbname":   "fcm_poc",
    "user":     "fcm_user",
    "password": "fcm_password",
}

NUM_ANALYSTS        = 120
NUM_CASES           = 5_000
NUM_ALERTS          = 15_000
SNAPSHOT_START_DATE = date(2024, 1, 1)
SNAPSHOT_END_DATE   = date(2026, 3, 24)   # today

random.seed(42)

# ── Helpers ───────────────────────────────────────────────────────────────────

def rnd_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def case_ref(n: int) -> str:
    return f"FCM-{2024 + (n // 3000)}-{n:07d}"


def sar_ref(n: int) -> str:
    return f"SAR-{2024 + (n // 1000)}-{n:06d}"


def alert_ref(n: int) -> str:
    return f"ALT-{2024 + (n // 5000)}-{n:07d}"


def analyst_code(n: int) -> str:
    return f"ANL-{n:05d}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Connecting to database …")
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    # ── 1. Fetch reference IDs ────────────────────────────────────────────────
    def fetch_ids(table, id_col):
        cur.execute(f"SELECT {id_col} FROM {table}")
        return [r[0] for r in cur.fetchall()]

    region_ids     = fetch_ids("dim_region",               "region_id")
    country_rows   = cur.execute(
        "SELECT country_id, region_id FROM dim_country") or cur.fetchall()
    country_map    = {}   # country_id -> region_id

    cur.execute("SELECT country_id, region_id FROM dim_country")
    for cid, rid in cur.fetchall():
        country_map[cid] = rid

    cur.execute("SELECT entity_id, country_id, region_id FROM dim_entity")
    entity_rows = cur.fetchall()   # [(entity_id, country_id, region_id)]

    cur.execute("SELECT team_id, region_id, entity_id FROM dim_team")
    team_rows = cur.fetchall()     # [(team_id, region_id, entity_id)]

    crime_type_ids = fetch_ids("dim_financial_crime_type", "crime_type_id")
    risk_class_rows = []
    cur.execute("SELECT risk_class_id, sla_days FROM dim_risk_classification")
    risk_class_rows = cur.fetchall()   # [(id, sla_days)]

    priority_ids   = fetch_ids("dim_priority",             "priority_id")
    source_ids     = fetch_ids("dim_case_source",          "source_id")
    channel_ids    = fetch_ids("dim_channel",              "channel_id")
    disposition_ids= fetch_ids("dim_disposition",          "disposition_id")

    # ── 2. Analysts ───────────────────────────────────────────────────────────
    print(f"Inserting {NUM_ANALYSTS} analysts …")
    grades = ["Analyst I","Analyst II","Analyst III","Senior Analyst","Lead Analyst","Manager"]
    analyst_data = []
    for i in range(1, NUM_ANALYSTS + 1):
        team_id = random.choice(team_rows)[0]
        analyst_data.append((
            analyst_code(i),
            f"Analyst {i:04d}",
            random.choice(grades),
            team_id,
            random.random() > 0.05   # 95% active
        ))
    execute_batch(cur, """
        INSERT INTO dim_analyst (analyst_code, display_name, grade, team_id, is_active)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (analyst_code) DO NOTHING
    """, analyst_data)
    conn.commit()

    cur.execute("SELECT analyst_id, team_id FROM dim_analyst")
    analyst_rows = cur.fetchall()   # [(analyst_id, team_id)]

    # ── 3. Cases ──────────────────────────────────────────────────────────────
    print(f"Inserting {NUM_CASES} cases …")

    open_statuses   = ["open","in_review","pending_information","escalated","pending_sar","pending_closure"]
    closed_statuses = ["closed","withdrawn"]
    all_statuses    = open_statuses + closed_statuses * 2   # bias toward closed

    workflow_stages = [
        "triage","initial_review","investigation","enhanced_due_diligence",
        "quality_assurance","senior_review","legal_review","regulatory_reporting",
        "closure_approval","closed"
    ]

    case_data = []
    for i in range(1, NUM_CASES + 1):
        entity   = random.choice(entity_rows)
        team     = random.choice(team_rows)
        analyst  = random.choice(analyst_rows)
        risk_row = random.choice(risk_class_rows)
        risk_id, sla_days = risk_row

        opened = rnd_date(date(2024, 1, 1), date(2026, 3, 1))
        review_due = opened + timedelta(days=sla_days)
        status = random.choice(all_statuses)

        if status in closed_statuses:
            extra = random.randint(0, int(sla_days * 1.5))
            closed = opened + timedelta(days=extra)
            stage  = "closed"
        else:
            closed = None
            stage  = random.choice(workflow_stages[:-1])  # exclude 'closed'

        escalated = None
        if status == "escalated" or random.random() < 0.08:
            escalated = opened + timedelta(days=random.randint(5, 20))

        crime_type_id = random.choice(crime_type_ids)
        channel_id    = random.choice(channel_ids)
        priority_id   = random.choice(priority_ids)
        source_id     = random.choice(source_ids)
        disposition_id= random.choice(disposition_ids) if status in closed_statuses else None

        est_val = round(random.uniform(10_000, 50_000_000), 2) if random.random() > 0.3 else None
        conf_loss = round(float(est_val) * random.uniform(0.1, 0.9), 2) if est_val and status == "closed" else None
        recovered = round(float(conf_loss) * random.uniform(0, 0.7), 2) if conf_loss else None

        # Compute SLA columns
        today = date(2026, 3, 24)
        actual_days = (closed - opened).days if closed else (today - opened).days
        sla_breached = actual_days > sla_days

        case_data.append((
            case_ref(i),
            f"Financial Crime Investigation - {crime_type_id}",
            crime_type_id,
            risk_id,
            priority_id,
            source_id,
            channel_id,
            entity[0],  entity[1], entity[2],   # entity_id, country_id, region_id
            team[0],                              # team_id
            analyst[0],                           # analyst_id
            opened,
            opened + timedelta(days=random.randint(0, 5)) if random.random() > 0.1 else None,
            opened + timedelta(days=random.randint(1, 10)) if random.random() > 0.2 else None,
            review_due,
            escalated,
            closed,
            status,
            stage,
            disposition_id,
            sla_days,
            actual_days,
            sla_breached,
            random.choice([True, False, False, False]),  # involves_pep (25%)
            random.choice([True, False, False, False, False]),  # sanctioned (20%)
            random.choice([True, True, False]),           # cross_border (66%)
            random.choice([True, False, False, False]),  # is_complex (25%)
            random.choice([True, False, False]),          # regulatory_notified (33%)
            est_val,
            conf_loss,
            recovered,
            random.randint(0, 3) if status == "closed" else 0,
            random.randint(0, 1) if random.random() < 0.05 else 0,
            random.randint(0, 8) if random.random() < 0.2 else 0,
        ))

    execute_batch(cur, """
        INSERT INTO fact_case (
            case_reference, case_title, crime_type_id, risk_class_id, priority_id,
            source_id, channel_id, entity_id, country_id, region_id,
            team_id, assigned_analyst_id,
            opened_date,
            assigned_date, first_action_date, review_due_date,
            escalated_date, closed_date,
            case_status, workflow_stage, disposition_id, sla_target_days,
            actual_days_open, is_sla_breached,
            involves_pep, involves_sanctioned_entity, cross_border,
            is_complex, regulatory_notified,
            estimated_value_usd, confirmed_loss_usd, recovered_usd,
            sar_count, law_enforcement_referrals, linked_case_count
        ) VALUES (
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,
            %s,%s,%s,
            %s,%s,%s,
            %s,%s,%s,%s,
            %s,%s,
            %s,%s,%s,
            %s,%s,
            %s,%s,%s,
            %s,%s,%s
        )
        ON CONFLICT (case_reference) DO NOTHING
    """, case_data)
    conn.commit()
    print(f"  {NUM_CASES} cases inserted.")

    # ── 4. Case Stage History ─────────────────────────────────────────────────
    print("Generating stage history …")
    cur.execute("SELECT case_id, opened_date, closed_date, workflow_stage FROM fact_case")
    cases_for_history = cur.fetchall()

    stage_order = [
        "triage","initial_review","investigation","enhanced_due_diligence",
        "quality_assurance","senior_review","legal_review","regulatory_reporting",
        "closure_approval","closed"
    ]

    history_data = []
    for case_id, opened, closed, current_stage in cases_for_history:
        max_stage_idx = stage_order.index(current_stage) if current_stage in stage_order else 0
        ts = opened
        for idx in range(max_stage_idx + 1):
            stage = stage_order[idx]
            entered = ts
            days_spent = random.randint(1, 8)
            exited = None
            if idx < max_stage_idx:
                from datetime import datetime
                entered_ts = datetime.combine(ts, __import__('datetime').time(9, 0))
                exited_ts  = datetime.combine(ts + timedelta(days=days_spent), __import__('datetime').time(17, 0))
                days_in = round((exited_ts - entered_ts).total_seconds() / 86400, 2)
                history_data.append((case_id, stage, entered_ts, exited_ts, days_in, random.choice([a[0] for a in analyst_rows])))
                ts = ts + timedelta(days=days_spent)
            else:
                from datetime import datetime
                entered_ts = datetime.combine(ts, __import__('datetime').time(9, 0))
                history_data.append((case_id, stage, entered_ts, None, None, random.choice([a[0] for a in analyst_rows])))

    execute_batch(cur, """
        INSERT INTO fact_case_stage_history (case_id, workflow_stage, stage_entered_at, stage_exited_at, days_in_stage, actor_analyst_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, history_data, page_size=500)
    conn.commit()
    print(f"  {len(history_data)} stage history records inserted.")

    # ── 5. SARs ───────────────────────────────────────────────────────────────
    print("Generating SARs …")
    cur.execute("""
        SELECT case_id, entity_id, country_id, team_id, assigned_analyst_id, crime_type_id, closed_date
        FROM fact_case
        WHERE sar_count > 0 AND closed_date IS NOT NULL
    """)
    sar_cases = cur.fetchall()
    sar_data = []
    sar_counter = 1
    authorities = ["NCA (UK)","FinCEN (USA)","AUSTRAC (AUS)","FINTRAC (CAN)","MAS (SGP)","JAFIC (JPN)","FCA (UK)"]
    sar_types = ["initial","addendum","defence_against_money_laundering"]
    sar_statuses = ["filed","acknowledged","queried","closed"]

    for case_id, entity_id, country_id, team_id, analyst_id, crime_type_id, closed_date in sar_cases:
        num_sars = random.randint(1, 3)
        base_date = closed_date if closed_date else date(2025, 1, 1)
        for j in range(num_sars):
            sar_data.append((
                sar_ref(sar_counter),
                case_id, entity_id, country_id, team_id,
                analyst_id if analyst_id else analyst_rows[0][0],
                base_date + timedelta(days=j),
                random.choice(authorities),
                sar_types[min(j, 2)],
                random.choice(sar_statuses),
                random.random() < 0.4,
                random.random() < 0.3 if random.random() < 0.4 else None,
                crime_type_id,
            ))
            sar_counter += 1

    execute_batch(cur, """
        INSERT INTO fact_sar (
            sar_reference, case_id, entity_id, country_id, team_id, analyst_id,
            filed_date, reporting_authority, sar_type, sar_status,
            consent_requested, consent_granted, crime_type_id
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (sar_reference) DO NOTHING
    """, sar_data)
    conn.commit()
    print(f"  {len(sar_data)} SARs inserted.")

    # ── 6. Alerts ─────────────────────────────────────────────────────────────
    print(f"Generating {NUM_ALERTS} alerts …")
    alert_types   = ["transaction_monitoring","sanctions_hit","pep_match","adverse_media",
                     "unusual_behaviour","fraud_indicator","kyc_expiry"]
    alert_statuses= ["open","in_review","escalated","closed_false_positive","closed_true_positive","merged"]
    cur.execute("SELECT case_id FROM fact_case ORDER BY RANDOM() LIMIT 3000")
    linkable_cases = [r[0] for r in cur.fetchall()]

    alert_data = []
    from datetime import datetime
    for i in range(1, NUM_ALERTS + 1):
        entity   = random.choice(entity_rows)
        alert_ts = datetime.combine(rnd_date(date(2024, 1, 1), date(2026, 3, 20)), __import__('datetime').time(random.randint(0,23), random.randint(0,59)))
        status   = random.choice(alert_statuses)
        reviewed_at = alert_ts + timedelta(minutes=random.randint(5, 10000)) if status != "open" else None
        resolution_minutes = int((reviewed_at - alert_ts).total_seconds() / 60) if reviewed_at else None
        linked_case = random.choice(linkable_cases) if status in ("escalated","closed_true_positive","merged") and linkable_cases else None

        alert_data.append((
            alert_ref(i),
            linked_case,
            random.choice(alert_types),
            random.randint(10, 100),
            status,
            entity[0], entity[1],
            random.choice(channel_ids),
            random.choice(crime_type_ids) if random.random() > 0.3 else None,
            round(random.uniform(100, 5_000_000), 2) if random.random() > 0.4 else None,
            alert_ts,
            reviewed_at,
            resolution_minutes,
        ))

    execute_batch(cur, """
        INSERT INTO fact_alert (
            alert_reference, case_id, alert_type, alert_score, alert_status,
            entity_id, country_id, channel_id, crime_type_id,
            transaction_amount_usd, alert_generated_at, reviewed_at, resolution_minutes
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (alert_reference) DO NOTHING
    """, alert_data, page_size=500)
    conn.commit()
    print(f"  {NUM_ALERTS} alerts inserted.")

    # ── 7. Daily aggregate snapshots ─────────────────────────────────────────
    print("Building daily aggregate snapshots (this may take a moment) …")
    cur.execute("""
        INSERT INTO agg_daily_case_snapshot (
            snapshot_date, region_id, country_id, entity_id, team_id,
            crime_type_id, risk_class_id,
            cases_open, cases_opened_today, cases_closed_today,
            cases_escalated, cases_in_sla, cases_sla_breached,
            cases_pending_info, cases_pending_sar,
            cases_triage, cases_initial_review, cases_investigation, cases_edd,
            cases_qa, cases_senior_review, cases_legal_review,
            cases_reg_reporting, cases_closure_approval,
            total_value_at_risk_usd, total_confirmed_loss_usd, total_recovered_usd,
            sars_filed, law_enforcement_referrals,
            avg_case_age_days
        )
        SELECT
            CURRENT_DATE                                         AS snapshot_date,
            fc.region_id,
            fc.country_id,
            fc.entity_id,
            fc.team_id,
            fc.crime_type_id,
            fc.risk_class_id,
            COUNT(*) FILTER (WHERE fc.case_status NOT IN ('closed','withdrawn'))  AS cases_open,
            COUNT(*) FILTER (WHERE fc.opened_date = CURRENT_DATE)                 AS cases_opened_today,
            COUNT(*) FILTER (WHERE fc.closed_date = CURRENT_DATE)                 AS cases_closed_today,
            COUNT(*) FILTER (WHERE fc.case_status = 'escalated')                  AS cases_escalated,
            COUNT(*) FILTER (WHERE NOT fc.is_sla_breached)                        AS cases_in_sla,
            COUNT(*) FILTER (WHERE fc.is_sla_breached)                            AS cases_sla_breached,
            COUNT(*) FILTER (WHERE fc.case_status = 'pending_information')        AS cases_pending_info,
            COUNT(*) FILTER (WHERE fc.case_status = 'pending_sar')                AS cases_pending_sar,
            COUNT(*) FILTER (WHERE fc.workflow_stage = 'triage')                  AS cases_triage,
            COUNT(*) FILTER (WHERE fc.workflow_stage = 'initial_review')          AS cases_initial_review,
            COUNT(*) FILTER (WHERE fc.workflow_stage = 'investigation')           AS cases_investigation,
            COUNT(*) FILTER (WHERE fc.workflow_stage = 'enhanced_due_diligence')  AS cases_edd,
            COUNT(*) FILTER (WHERE fc.workflow_stage = 'quality_assurance')       AS cases_qa,
            COUNT(*) FILTER (WHERE fc.workflow_stage = 'senior_review')           AS cases_senior_review,
            COUNT(*) FILTER (WHERE fc.workflow_stage = 'legal_review')            AS cases_legal_review,
            COUNT(*) FILTER (WHERE fc.workflow_stage = 'regulatory_reporting')    AS cases_reg_reporting,
            COUNT(*) FILTER (WHERE fc.workflow_stage = 'closure_approval')        AS cases_closure_approval,
            COALESCE(SUM(fc.estimated_value_usd) FILTER (WHERE fc.case_status NOT IN ('closed','withdrawn')), 0) AS total_value_at_risk_usd,
            COALESCE(SUM(fc.confirmed_loss_usd), 0)                               AS total_confirmed_loss_usd,
            COALESCE(SUM(fc.recovered_usd), 0)                                    AS total_recovered_usd,
            COALESCE(SUM(fc.sar_count), 0)                                        AS sars_filed,
            COALESCE(SUM(fc.law_enforcement_referrals), 0)                        AS law_enforcement_referrals,
            AVG(fc.actual_days_open)                                               AS avg_case_age_days
        FROM fact_case fc
        GROUP BY fc.region_id, fc.country_id, fc.entity_id, fc.team_id,
                 fc.crime_type_id, fc.risk_class_id
        ON CONFLICT DO NOTHING
    """)
    conn.commit()
    print("  Snapshots inserted.")

    cur.close()
    conn.close()
    print("\n✓ Sample data generation complete.")


if __name__ == "__main__":
    main()
