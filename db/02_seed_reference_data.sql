-- =============================================================================
-- Reference Data Seed
-- =============================================================================

-- REGIONS
INSERT INTO dim_region (region_code, region_name, timezone) VALUES
  ('EMEA',  'Europe, Middle East & Africa',    'Europe/London'),
  ('APAC',  'Asia-Pacific',                     'Asia/Singapore'),
  ('AMER',  'Americas',                          'America/New_York'),
  ('LATAM', 'Latin America',                    'America/Sao_Paulo');

-- COUNTRIES (ISO 3166-1 alpha-3 sample)
INSERT INTO dim_country (country_code, country_name, region_id, is_high_risk, fatf_status) VALUES
  ('GBR', 'United Kingdom',      1, FALSE, 'compliant'),
  ('DEU', 'Germany',             1, FALSE, 'compliant'),
  ('FRA', 'France',              1, FALSE, 'compliant'),
  ('CHE', 'Switzerland',        1, FALSE, 'compliant'),
  ('NLD', 'Netherlands',        1, FALSE, 'compliant'),
  ('ARE', 'United Arab Emirates',1, TRUE,  'grey_list'),
  ('ZAF', 'South Africa',       1, FALSE, 'grey_list'),
  ('NGA', 'Nigeria',            1, TRUE,  'grey_list'),
  ('SGP', 'Singapore',          2, FALSE, 'compliant'),
  ('HKG', 'Hong Kong',          2, FALSE, 'compliant'),
  ('AUS', 'Australia',          2, FALSE, 'compliant'),
  ('IND', 'India',              2, FALSE, 'compliant'),
  ('JPN', 'Japan',              2, FALSE, 'compliant'),
  ('CHN', 'China',              2, FALSE, 'compliant'),
  ('USA', 'United States',      3, FALSE, 'compliant'),
  ('CAN', 'Canada',             3, FALSE, 'compliant'),
  ('BRA', 'Brazil',             4, FALSE, 'compliant'),
  ('MEX', 'Mexico',             4, FALSE, 'compliant'),
  ('COL', 'Colombia',           4, TRUE,  'grey_list'),
  ('PAN', 'Panama',             4, TRUE,  'grey_list');

-- ENTITIES (legal entities / branches)
INSERT INTO dim_entity (entity_code, entity_name, entity_type, country_id, region_id) VALUES
  ('GBR-HQ',    'Global HQ - London',          'legal_entity', 1,  1),
  ('DEU-BANK',  'Deutsche Operations GmbH',    'subsidiary',   2,  1),
  ('CHE-PB',    'Swiss Private Banking AG',    'subsidiary',   4,  1),
  ('ARE-DIFC',  'DIFC Branch',                 'branch',       6,  1),
  ('SGP-APAC',  'APAC Regional HQ Singapore',  'legal_entity', 9,  2),
  ('HKG-CORP',  'Hong Kong Corporate Branch',  'branch',       10, 2),
  ('AUS-RETAIL','Australia Retail Banking',     'subsidiary',   11, 2),
  ('USA-NYC',   'North America HQ - New York',  'legal_entity', 15, 3),
  ('CAN-ON',    'Canada Operations Toronto',   'branch',       16, 3),
  ('BRA-SP',    'Brazil Operations São Paulo', 'subsidiary',   17, 4);

-- TEAMS
INSERT INTO dim_team (team_code, team_name, team_type, region_id, entity_id, manager_name, headcount) VALUES
  ('EMEA-AML-1',  'EMEA AML Investigations Alpha',      'aml_investigations',      1, 1, 'Sarah Thornton',    12),
  ('EMEA-AML-2',  'EMEA AML Investigations Beta',       'aml_investigations',      1, 1, 'James Okafor',      10),
  ('EMEA-SANC',   'EMEA Sanctions Screening',           'sanctions_screening',     1, 1, 'Priya Mehta',        8),
  ('EMEA-FRAUD',  'EMEA Fraud Operations',              'fraud_operations',        1, 2, 'Marco Bianchi',     14),
  ('EMEA-KYC',    'EMEA KYC Remediation',               'kyc_remediation',         1, 3, 'Anneliese Koch',     9),
  ('EMEA-FIU',    'EMEA Financial Intelligence Unit',   'financial_intelligence',  1, 1, 'David Ashworth',     6),
  ('APAC-AML-1',  'APAC AML Investigations',            'aml_investigations',      2, 5, 'Li Wei',            11),
  ('APAC-SANC',   'APAC Sanctions Screening',           'sanctions_screening',     2, 5, 'Ravi Krishnan',      7),
  ('APAC-FRAUD',  'APAC Fraud Operations',              'fraud_operations',        2, 6, 'Mei Ling Chan',     10),
  ('APAC-KYC',    'APAC KYC Remediation',               'kyc_remediation',         2, 5, 'Aiko Tanaka',        8),
  ('AMER-AML',    'Americas AML Investigations',        'aml_investigations',      3, 8, 'Robert Kennedy',    13),
  ('AMER-SANC',   'Americas Sanctions Screening',       'sanctions_screening',     3, 8, 'Maria Gonzalez',     9),
  ('AMER-FRAUD',  'Americas Fraud Operations',          'fraud_operations',        3, 8, 'Tyler Brooks',      12),
  ('LATAM-AML',   'LATAM AML Investigations',           'aml_investigations',      4, 10,'Isabela Ferreira',   8),
  ('LATAM-KYC',   'LATAM KYC Remediation',              'kyc_remediation',         4, 10,'Carlos Navarro',      6);

-- FINANCIAL CRIME TYPES
INSERT INTO dim_financial_crime_type (crime_type_code, crime_type_name, crime_category, regulatory_framework, is_sar_reportable) VALUES
  ('ML-LAYERING',   'Money Laundering - Layering',           'money_laundering',        'POCA/MLR2017',    TRUE),
  ('ML-PLACEMENT',  'Money Laundering - Placement',          'money_laundering',        'POCA/MLR2017',    TRUE),
  ('ML-INTEGRATION','Money Laundering - Integration',        'money_laundering',        'POCA/MLR2017',    TRUE),
  ('OFAC-SDN',      'OFAC SDN Sanctions Hit',                'sanctions_evasion',       'OFAC',            FALSE),
  ('EU-SANC',       'EU Sanctions Breach',                   'sanctions_evasion',       'EU_AMLD6',        FALSE),
  ('UN-SANC',       'UN Sanctions Evasion',                  'sanctions_evasion',       'UN_Security',     FALSE),
  ('FRAUD-CARD',    'Card & Payments Fraud',                 'fraud',                   'PSD2',            TRUE),
  ('FRAUD-ID',      'Identity Theft / Impersonation',        'fraud',                   'MLR2017',         TRUE),
  ('FRAUD-TRADE',   'Trade-Based Money Laundering',          'fraud',                   'MLR2017',         TRUE),
  ('FRAUD-CYBER',   'Cyber-Enabled Fraud',                   'cybercrime',              'NIS2',            TRUE),
  ('TF-DIRECT',     'Direct Terrorist Financing',            'terrorist_financing',     'TACT',            TRUE),
  ('TF-INDIRECT',   'Indirect Terrorist Financing',          'terrorist_financing',     'TACT',            TRUE),
  ('PROLIF',        'Proliferation Financing',               'proliferation_financing', 'UN_1540',         TRUE),
  ('BRIBERY',       'Bribery & Corruption',                  'bribery_corruption',      'UKBA2010',        TRUE),
  ('TAX-EVASION',   'Tax Evasion',                           'tax_evasion',             'CJPOA2017',       TRUE),
  ('MARKET-ABUSE',  'Market Abuse / Insider Dealing',        'market_abuse',            'MAR/MiFID',       FALSE),
  ('HT-FINANCE',    'Human Trafficking Finance',             'human_trafficking',       'MSA2015',         TRUE),
  ('CRYPTO-ML',     'Crypto-Asset Money Laundering',        'money_laundering',        'MiCA/MLR2022',    TRUE);

-- RISK CLASSIFICATIONS
INSERT INTO dim_risk_classification (risk_level, risk_score_min, risk_score_max, sla_days, escalation_days) VALUES
  ('low',      1,  25,  90, 75),
  ('medium',  26,  50,  60, 45),
  ('high',    51,  75,  30, 20),
  ('critical',76, 100,  10,  5);

-- PRIORITIES
INSERT INTO dim_priority (priority_name, description, response_hours) VALUES
  ('P1', 'Immediate - law enforcement / regulator involved',  2),
  ('P2', 'High - confirmed crime or sanctions match',         8),
  ('P3', 'Standard - investigation required',                48),
  ('P4', 'Low - review & monitor',                          120);

-- CASE SOURCES
INSERT INTO dim_case_source (source_code, source_name, source_category) VALUES
  ('TM-ALERT',   'Transaction Monitoring Alert',     'transaction_monitoring'),
  ('SANC-SCREEN','Sanctions Screening Hit',          'automated_alert'),
  ('PEP-MATCH',  'PEP Database Match',               'automated_alert'),
  ('ADV-MEDIA',  'Adverse Media Alert',              'automated_alert'),
  ('STAFF-REF',  'Staff Referral',                   'human_referral'),
  ('CUSTOMER',   'Customer Self-Disclosure',         'customer_disclosure'),
  ('INTERNAL',   'Internal Audit Finding',           'internal_audit'),
  ('LEA-REQ',    'Law Enforcement Request',          'regulatory'),
  ('REG-NOTIF',  'Regulatory Notification',          'regulatory'),
  ('DAML',       'DAML / Consent Request',           'regulatory');

-- DISPOSITIONS
INSERT INTO dim_disposition (disposition_code, disposition_name, requires_sar, requires_restraint, is_closed) VALUES
  ('SAR-FILED',       'SAR Filed - Reported to Regulator',                TRUE,  FALSE, TRUE),
  ('DAML-CONSENT',    'DAML Consent Obtained - Transaction Proceeds',     TRUE,  FALSE, TRUE),
  ('LEA-REFER',       'Referred to Law Enforcement',                      TRUE,  FALSE, TRUE),
  ('NO-FURTHER',      'No Further Action - No Suspicion',                 FALSE, FALSE, TRUE),
  ('MONITOR',         'Enhanced Monitoring Imposed',                      FALSE, FALSE, TRUE),
  ('EXIT-CLIENT',     'Client Relationship Exited',                       TRUE,  FALSE, TRUE),
  ('FUND-FROZEN',     'Funds Frozen / Assets Restrained',                 TRUE,  TRUE,  TRUE),
  ('FALSE-POS',       'False Positive - Alert Closed',                    FALSE, FALSE, TRUE),
  ('ESCALATED',       'Escalated to FIU / Senior Management',             FALSE, FALSE, FALSE),
  ('WITHDRAWN',       'Case Withdrawn - Duplicate',                       FALSE, FALSE, TRUE);

-- BUSINESS CHANNELS
INSERT INTO dim_channel (channel_code, channel_name) VALUES
  ('RETAIL',   'retail_banking'),
  ('CORP',     'corporate_banking'),
  ('WEALTH',   'wealth_management'),
  ('TRADE',    'trade_finance'),
  ('DIGITAL',  'digital_banking'),
  ('CORRES',   'correspondent_banking'),
  ('IB',       'investment_banking'),
  ('INSUR',    'insurance');
