#!/bin/bash
# =============================================================================
# Superset post-init: registers the FCM database connection and
# creates role hierarchy for the financial crime team structure.
# =============================================================================
set -e

FCM_DB_URI="${FCM_DB_URI:-postgresql+psycopg2://fcm_user:fcm_password@postgres:5432/fcm_poc}"

echo "=== Registering FCM database connection ==="
superset set-database-uri \
  --database-name "FCM Case Management DB" \
  --uri "$FCM_DB_URI" 2>/dev/null || true

echo "=== Creating role hierarchy ==="

# Analyst (read-only: explore charts, view dashboards, run SQL on FCM DB)
superset fab create-permission-view --view "Superset" --permission "menu_access" 2>/dev/null || true
superset fab add-role --name "FCM_Analyst" 2>/dev/null || true

# Team Lead (can create/edit charts and dashboards)
superset fab add-role --name "FCM_TeamLead" 2>/dev/null || true

# Compliance Manager (all Analyst + Team Lead perms + user management)
superset fab add-role --name "FCM_ComplianceManager" 2>/dev/null || true

# FIU / Global View (unrestricted read across all entities/regions)
superset fab add-role --name "FCM_FIU" 2>/dev/null || true

echo "=== Superset init complete ==="
