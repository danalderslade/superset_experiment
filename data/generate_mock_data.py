#!/usr/bin/env python3
"""
generate_mock_data.py
---------------------
Generates realistic mock data for the Financial Crime Case Management
database (multi-region / multi-market).

Run:
    python3 data/generate_mock_data.py > data/mock_data.sql

The script is deterministic (seeded) so re-running always produces
the same output.
"""

import random
import string
from datetime import date, timedelta, datetime

random.seed(42)

# ── helpers ────────────────────────────────────────────────────────────────

def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def rand_datetime(start: date, end: date) -> datetime:
    d = rand_date(start, end)
    h = random.randint(7, 19)
    m = random.randint(0, 59)
    return datetime(d.year, d.month, d.day, h, m)

def sql_str(v) -> str:
    if v is None:
        return "NULL"
    s = str(v).replace("'", "''")
    return f"'{s}'"

def sql_bool(v: bool) -> str:
    return "TRUE" if v else "FALSE"

def sql_date(d) -> str:
    return "NULL" if d is None else f"'{d.isoformat()}'"

def sql_num(v, decimals=2) -> str:
    return "NULL" if v is None else str(round(v, decimals))

def rand_id(prefix: str, length=8) -> str:
    return prefix + "".join(random.choices(string.digits, k=length))

# ── reference data ─────────────────────────────────────────────────────────

REGIONS = [
    ("NOAM",  "North America"),
    ("EMEA",  "Europe, Middle East & Africa"),
    ("APAC",  "Asia Pacific"),
    ("LATAM", "Latin America"),
]

MARKETS = [
    # (code, name, region_code, currency)
    ("US",  "United States",   "NOAM",  "USD"),
    ("CA",  "Canada",          "NOAM",  "CAD"),
    ("MX",  "Mexico",          "NOAM",  "MXN"),
    ("GB",  "United Kingdom",  "EMEA",  "GBP"),
    ("DE",  "Germany",         "EMEA",  "EUR"),
    ("FR",  "France",          "EMEA",  "EUR"),
    ("NL",  "Netherlands",     "EMEA",  "EUR"),
    ("CH",  "Switzerland",     "EMEA",  "CHF"),
    ("AE",  "UAE",             "EMEA",  "AED"),
    ("ZA",  "South Africa",    "EMEA",  "ZAR"),
    ("SG",  "Singapore",       "APAC",  "SGD"),
    ("HK",  "Hong Kong",       "APAC",  "HKD"),
    ("AU",  "Australia",       "APAC",  "AUD"),
    ("JP",  "Japan",           "APAC",  "JPY"),
    ("BR",  "Brazil",          "LATAM", "BRL"),
    ("CO",  "Colombia",        "LATAM", "COP"),
    ("CL",  "Chile",           "LATAM", "CLP"),
]

CASE_TYPES = [
    # (code, name, category)
    ("AML_STRUCT",    "Structuring / Smurfing",             "AML"),
    ("AML_ML",        "Money Laundering",                   "AML"),
    ("AML_TF",        "Terrorist Financing",                "AML"),
    ("AML_PEP",       "PEP-Related Activity",               "AML"),
    ("FRAUD_ID",      "Identity Fraud",                     "Fraud"),
    ("FRAUD_CARD",    "Card Fraud",                         "Fraud"),
    ("FRAUD_WIRE",    "Wire Fraud",                         "Fraud"),
    ("FRAUD_APP",     "Application Fraud",                  "Fraud"),
    ("FRAUD_BEC",     "Business Email Compromise",          "Fraud"),
    ("SANCTIONS_HIT", "Sanctions Match",                    "Sanctions"),
    ("SANCTIONS_EVA", "Sanctions Evasion",                  "Sanctions"),
    ("CORRUPTION",    "Bribery / Corruption",               "Corruption"),
    ("TAX_EVASION",   "Tax Evasion",                        "Other"),
    ("INSIDER",       "Insider Threat",                     "Other"),
    ("CRYPTO",        "Illicit Crypto Activity",            "AML"),
]

ANALYST_POOL = [
    ("ANA001", "Alice Thornton",    "Level 1"),
    ("ANA002", "Ben Castillo",      "Level 1"),
    ("ANA003", "Cara Liu",          "Level 1"),
    ("ANA004", "David Mensah",      "Level 2"),
    ("ANA005", "Elena Petrov",      "Level 2"),
    ("ANA006", "Faisal Al-Farsi",   "Level 2"),
    ("ANA007", "Grace Kim",         "Level 2"),
    ("ANA008", "Hugo Rossi",        "Level 3"),
    ("ANA009", "Isabelle Bernard",  "Level 3"),
    ("ANA010", "James Oduya",       "Level 3"),
    ("ANA011", "Keiko Nakamura",    "Level 1"),
    ("ANA012", "Liam O'Brien",      "Level 1"),
    ("ANA013", "Maya Sharma",       "Level 2"),
    ("ANA014", "Nils Johansson",    "Level 2"),
    ("ANA015", "Olivia Chen",       "Level 3"),
    ("ANA016", "Paulo Ferreira",    "Level 1"),
    ("ANA017", "Quinn Taylor",      "Level 1"),
    ("ANA018", "Rania Khalil",      "Level 2"),
    ("ANA019", "Sofia Morales",     "Level 2"),
    ("ANA020", "Thomas Diallo",     "Level 3"),
]

# Distribute analysts across markets
ANALYST_MARKETS = {
    "ANA001": "US", "ANA002": "US", "ANA003": "CA",
    "ANA004": "GB", "ANA005": "DE", "ANA006": "AE",
    "ANA007": "SG", "ANA008": "US", "ANA009": "FR",
    "ANA010": "AU", "ANA011": "HK", "ANA012": "GB",
    "ANA013": "NL",
    "ANA014": "CH", "ANA015": "JP", "ANA016": "BR",
    "ANA017": "MX", "ANA018": "ZA", "ANA019": "CO",
    "ANA020": "US",
}

STATUSES = ["Open", "In Review", "Escalated", "Closed - SAR Filed", "Closed - No Action"]
STATUS_WEIGHTS = [0.20, 0.30, 0.10, 0.25, 0.15]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
PRIORITY_WEIGHTS = [0.25, 0.40, 0.25, 0.10]
CLOSURE_REASONS = ["SAR Filed", "No Action Required", "Referred to Law Enforcement",
                   "False Positive", "Duplicate"]
ALERT_TYPES = ["Structuring", "High Value Cash", "Unusual Pattern", "Sanctions Hit",
               "PEP Activity", "Rapid Movement", "Layering", "Round Dollar Amounts",
               "Geographic Risk", "New Account Activity"]
ALERT_SOURCES = ["Transaction Monitoring", "Screening System", "Manual Review",
                 "Tip-off", "Correspondent Bank", "Regulatory Referral"]
ALERT_DISPOSITIONS = ["True Positive", "False Positive", "Escalated", "Under Review"]
TXN_TYPES = ["Wire Transfer", "SWIFT", "Cash Deposit", "Cash Withdrawal",
             "Card Payment", "Crypto Transfer", "Internal Transfer", "ACH", "CHAPS"]
TXN_CHANNELS = ["Online Banking", "Branch", "ATM", "Mobile", "Correspondent", "API"]
ACTION_TYPES = ["Initial Review", "Document Request", "Customer Interview",
                "Escalation", "SAR Draft", "Peer Review", "Supervisor Sign-off",
                "System Search", "Closure - Approved", "Adverse Media Check"]
NATIONALITIES = ["USA", "GBR", "DEU", "FRA", "CHN", "IND", "NGA", "BRA", "MEX",
                 "RUS", "PAK", "IRN", "PRK", "SAU", "ARE", "SGP", "HKG", "AUS",
                 "ZAF", "COL", "CHL", "JPN", "CAN", "CHE", "NLD"]
RISK_RATINGS = ["Low", "Medium", "High", "PEP", "Sanctioned"]
RISK_RATING_WEIGHTS = [0.35, 0.30, 0.20, 0.10, 0.05]
SUBJECT_TYPES = ["Individual", "Corporate", "Government"]
SUBJECT_TYPE_WEIGHTS = [0.55, 0.40, 0.05]
ID_TYPES = ["Passport", "National ID", "Driver's Licence", "Company Registration",
            "Tax ID", "LEI"]

# FX rates to USD (approximate)
FX_TO_USD = {
    "USD": 1.0, "CAD": 0.74, "MXN": 0.057, "GBP": 1.27, "EUR": 1.09,
    "CHF": 1.13, "AED": 0.27, "ZAR": 0.053, "SGD": 0.75, "HKD": 0.13,
    "AUD": 0.65, "JPY": 0.0067, "BRL": 0.20, "COP": 0.00025, "CLP": 0.0011,
}

START_DATE = date(2022, 1, 1)
END_DATE   = date(2025, 12, 31)
NUM_CASES  = 2000

# ── build lookup maps ───────────────────────────────────────────────────────

region_id_map  = {r[0]: i+1 for i, r in enumerate(REGIONS)}
market_id_map  = {m[0]: i+1 for i, m in enumerate(MARKETS)}
case_type_id_map = {c[0]: i+1 for i, c in enumerate(CASE_TYPES)}
market_currency  = {m[0]: m[3] for m in MARKETS}
analyst_id_map = {a[0]: i+1 for i, a in enumerate(ANALYST_POOL)}

# ── SQL generation ──────────────────────────────────────────────────────────

lines = []
lines.append("-- Auto-generated mock data for financial crime case management")
lines.append("-- DO NOT edit by hand – regenerate using data/generate_mock_data.py")
lines.append("")

# 1. Regions
lines.append("-- Regions")
lines.append("INSERT INTO dim_region (region_code, region_name) VALUES")
vals = [f"({sql_str(r[0])}, {sql_str(r[1])})" for r in REGIONS]
lines.append(",\n".join(vals) + ";")
lines.append("")

# 2. Markets
lines.append("-- Markets")
lines.append("INSERT INTO dim_market (market_code, market_name, region_id, currency) VALUES")
vals = [f"({sql_str(m[0])}, {sql_str(m[1])}, {region_id_map[m[2]]}, {sql_str(m[3])})"
        for m in MARKETS]
lines.append(",\n".join(vals) + ";")
lines.append("")

# 3. Case types
lines.append("-- Case types")
lines.append("INSERT INTO dim_case_type (case_type_code, case_type_name, category) VALUES")
vals = [f"({sql_str(c[0])}, {sql_str(c[1])}, {sql_str(c[2])})" for c in CASE_TYPES]
lines.append(",\n".join(vals) + ";")
lines.append("")

# 4. Analysts
lines.append("-- Analysts")
lines.append("INSERT INTO dim_analyst (analyst_code, full_name, team, market_id, is_active) VALUES")
vals = []
for a in ANALYST_POOL:
    mkt = ANALYST_MARKETS[a[0]]
    vals.append(f"({sql_str(a[0])}, {sql_str(a[1])}, {sql_str(a[2])}, {market_id_map[mkt]}, TRUE)")
lines.append(",\n".join(vals) + ";")
lines.append("")

# 5. Cases
lines.append("-- Cases (fact_case)")
case_rows = []
case_ids_used = []

market_codes = [m[0] for m in MARKETS]
case_type_codes = [c[0] for c in CASE_TYPES]
analyst_codes = [a[0] for a in ANALYST_POOL]

for i in range(1, NUM_CASES + 1):
    case_ref = f"FC-{2022 + (i % 4)}-{i:06d}"
    ct_code  = random.choice(case_type_codes)
    mkt_code = random.choice(market_codes)
    status   = random.choices(STATUSES, STATUS_WEIGHTS)[0]
    priority = random.choices(PRIORITIES, PRIORITY_WEIGHTS)[0]
    risk     = round(random.uniform(10, 100), 2)
    analyst  = random.choice(analyst_codes)

    opened   = rand_date(START_DATE, END_DATE)
    closed   = None
    closure  = None
    is_sar   = False
    is_reg   = False

    if "Closed" in status:
        closed_days = random.randint(5, 180)
        closed = opened + timedelta(days=closed_days)
        if closed > END_DATE:
            closed = END_DATE
        closure = random.choice(CLOSURE_REASONS)
        if status == "Closed - SAR Filed":
            is_sar = True
            is_reg = random.random() < 0.6

    last_updated = rand_datetime(opened, closed or END_DATE)

    row = (
        f"({sql_str(case_ref)}, {case_type_id_map[ct_code]}, {market_id_map[mkt_code]}, "
        f"{sql_str(status)}, {sql_str(priority)}, {sql_num(risk)}, "
        f"{analyst_id_map[analyst]}, {sql_date(opened)}, "
        f"'{last_updated.isoformat(sep=' ')[:19]}', "
        f"{sql_date(closed)}, {sql_str(closure)}, "
        f"{sql_bool(is_sar)}, {sql_bool(is_reg)}, NULL)"
    )
    case_rows.append(row)
    case_ids_used.append((i, mkt_code))

lines.append("INSERT INTO fact_case "
             "(case_reference, case_type_id, market_id, status, priority, risk_score, "
             "assigned_analyst, opened_date, last_updated, closed_date, closure_reason, "
             "is_sar_filed, is_regulatory_report, notes) VALUES")
lines.append(",\n".join(case_rows) + ";")
lines.append("")

# 6. Subjects
lines.append("-- Subjects (fact_subject)")
subj_rows = []
for (case_idx, mkt_code) in case_ids_used:
    n_subjects = random.randint(1, 3)
    for _ in range(n_subjects):
        stype = random.choices(SUBJECT_TYPES, SUBJECT_TYPE_WEIGHTS)[0]
        nat   = random.choice(NATIONALITIES)
        cres  = random.choice(NATIONALITIES)
        rr    = random.choices(RISK_RATINGS, RISK_RATING_WEIGHTS)[0]
        is_pep = rr == "PEP"
        is_san = rr == "Sanctioned"
        id_t  = random.choice(ID_TYPES)
        id_n  = rand_id("ID", 10)
        dob   = rand_date(date(1950, 1, 1), date(1999, 12, 31)) if stype == "Individual" else None
        name  = f"Subject-{rand_id('', 6)}"
        row = (
            f"({case_idx}, {sql_str(stype)}, {sql_str(name)}, "
            f"{sql_date(dob)}, {sql_str(nat)}, {sql_str(cres)}, "
            f"{sql_str(id_t)}, {sql_str(id_n)}, {sql_str(rr)}, "
            f"{sql_bool(is_pep)}, {sql_bool(is_san)})"
        )
        subj_rows.append(row)

lines.append("INSERT INTO fact_subject "
             "(case_id, subject_type, full_name, date_of_birth, nationality, country_of_res, "
             "id_type, id_number, risk_rating, is_pep, is_sanctioned) VALUES")
lines.append(",\n".join(subj_rows) + ";")
lines.append("")

# 7. Alerts
lines.append("-- Alerts (fact_alert)")
alert_rows = []
alert_counter = 1
for (case_idx, mkt_code) in case_ids_used:
    n_alerts = random.randint(1, 4)
    currency = market_currency[mkt_code]
    for _ in range(n_alerts):
        aref  = f"ALT-{alert_counter:07d}"
        atype = random.choice(ALERT_TYPES)
        adate = rand_date(START_DATE, END_DATE)
        asrc  = random.choice(ALERT_SOURCES)
        amt   = round(random.uniform(1000, 5_000_000), 2)
        disp  = None
        ast   = "Pending"
        if random.random() < 0.7:
            disp = random.choice(ALERT_DISPOSITIONS)
            ast  = "Closed" if disp in ("True Positive", "False Positive") else "Assigned"
        row = (
            f"({case_idx if random.random() < 0.8 else 'NULL'}, "
            f"{sql_str(aref)}, {sql_str(atype)}, {sql_date(adate)}, "
            f"{sql_str(asrc)}, {sql_num(amt)}, {sql_str(currency)}, "
            f"{market_id_map[mkt_code]}, {sql_str(ast)}, {sql_str(disp)})"
        )
        alert_rows.append(row)
        alert_counter += 1

lines.append("INSERT INTO fact_alert "
             "(case_id, alert_reference, alert_type, alert_date, alert_source, amount, currency, "
             "market_id, status, disposition) VALUES")
lines.append(",\n".join(alert_rows) + ";")
lines.append("")

# 8. Transactions
lines.append("-- Transactions (fact_transaction)")
txn_rows = []
txn_counter = 1
countries = [m[0] for m in MARKETS] + ["CN", "IN", "RU", "NG", "PK", "IR"]

for (case_idx, mkt_code) in case_ids_used:
    n_txns = random.randint(2, 8)
    currency = market_currency[mkt_code]
    fx = FX_TO_USD.get(currency, 1.0)
    for _ in range(n_txns):
        tref   = f"TXN-{txn_counter:08d}"
        tdate  = rand_date(START_DATE, END_DATE)
        ttype  = random.choice(TXN_TYPES)
        amt    = round(random.uniform(500, 2_000_000), 2)
        amt_usd = round(amt * fx, 2)
        from_c = random.choice(countries)
        to_c   = random.choice(countries)
        chan   = random.choice(TXN_CHANNELS)
        is_sus = random.random() < 0.35
        row = (
            f"({case_idx}, {sql_str(tref)}, {sql_date(tdate)}, {sql_str(ttype)}, "
            f"{sql_num(amt)}, {sql_num(amt_usd)}, {sql_str(currency)}, "
            f"{sql_str(rand_id('ACC', 10))}, {sql_str('Bank-' + rand_id('', 4))}, "
            f"{sql_str(from_c)}, "
            f"{sql_str(rand_id('ACC', 10))}, {sql_str('Bank-' + rand_id('', 4))}, "
            f"{sql_str(to_c)}, "
            f"{sql_str(chan)}, {sql_bool(is_sus)})"
        )
        txn_rows.append(row)
        txn_counter += 1

lines.append("INSERT INTO fact_transaction "
             "(case_id, txn_reference, txn_date, txn_type, amount, amount_usd, currency, "
             "from_account, from_institution, from_country, "
             "to_account, to_institution, to_country, "
             "channel, is_suspicious) VALUES")
lines.append(",\n".join(txn_rows) + ";")
lines.append("")

# 9. Investigation actions
lines.append("-- Investigation actions (fact_investigation_action)")
inv_rows = []
for (case_idx, mkt_code) in case_ids_used:
    n_actions = random.randint(2, 6)
    action_date_base = rand_date(START_DATE, END_DATE)
    for j in range(n_actions):
        adt = datetime(
            action_date_base.year, action_date_base.month, action_date_base.day,
            random.randint(8, 18), random.randint(0, 59)
        ) + timedelta(days=j * random.randint(1, 7))
        if adt.date() > END_DATE:
            adt = datetime(END_DATE.year, END_DATE.month, END_DATE.day, 17, 0)
        analyst = random.choice(analyst_codes)
        atype   = ACTION_TYPES[j] if j < len(ACTION_TYPES) else random.choice(ACTION_TYPES)
        outcome = random.choice(["Completed", "Pending", "Escalated", None])
        row = (
            f"({case_idx}, {analyst_id_map[analyst]}, "
            f"'{adt.isoformat(sep=' ')[:19]}', "
            f"{sql_str(atype)}, NULL, {sql_str(outcome)})"
        )
        inv_rows.append(row)

lines.append("INSERT INTO fact_investigation_action "
             "(case_id, analyst_id, action_date, action_type, action_detail, outcome) VALUES")
lines.append(",\n".join(inv_rows) + ";")
lines.append("")

print("\n".join(lines))
