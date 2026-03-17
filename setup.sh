#!/usr/bin/env bash
# setup.sh – one-shot bootstrap for Apache Superset + Financial Crime dataset
# Usage: bash setup.sh
set -e

echo "=================================================="
echo " Apache Superset – Financial Crime Experiment"
echo "=================================================="
echo ""

# Check prerequisites
command -v docker  >/dev/null 2>&1 || { echo "ERROR: docker not found. Install Docker Desktop first."; exit 1; }
command -v docker-compose >/dev/null 2>&1 \
  || docker compose version >/dev/null 2>&1 \
  || { echo "ERROR: docker-compose not found."; exit 1; }

COMPOSE="docker compose"
docker compose version >/dev/null 2>&1 || COMPOSE="docker-compose"

# Ensure .env exists with a SECRET_KEY
if [ ! -f .env ]; then
  echo "No .env file found – creating one from .env.example with a generated SECRET_KEY..."
  cp .env.example .env
  if command -v python3 >/dev/null 2>&1; then
    GENERATED_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(42))")
    sed -i "s|CHANGE_ME_generate_a_strong_random_secret_key|${GENERATED_KEY}|" .env
    echo "   Generated SECRET_KEY written to .env"
  else
    echo "WARNING: python3 not found. Edit .env and set a strong SECRET_KEY before continuing."
  fi
fi

echo "1. Pulling images (this may take a few minutes on first run)..."
$COMPOSE pull --quiet

echo "2. Starting database and Redis..."
$COMPOSE up -d db mock_data_db redis

echo "3. Waiting for mock_data_db to be ready..."
for i in $(seq 1 40); do
  $COMPOSE exec -T mock_data_db pg_isready -U "${MOCK_DB_USER:-analyst}" -d "${MOCK_DB_NAME:-financial_crime}" >/dev/null 2>&1 \
    && echo "   mock_data_db is ready." && break
  echo "   Waiting... ($i/40)"
  sleep 5
done

echo "4. Initialising Superset (creating admin user, running migrations)..."
$COMPOSE up superset-init
# Wait for init container to finish
$COMPOSE wait superset-init 2>/dev/null || true

echo "5. Starting all services..."
$COMPOSE up -d

echo ""
echo "=================================================="
echo " Setup complete!"
echo "=================================================="
echo ""
echo " Superset URL : http://localhost:8088"
echo " Username     : ${ADMIN_USERNAME:-admin}"
echo " Password     : ${ADMIN_PASSWORD:-admin}"
echo ""
echo " Mock database connection string (add in Superset -> Settings -> Database Connections):"
echo "   postgresql+psycopg2://${MOCK_DB_USER:-analyst}:${MOCK_DB_PASSWORD:-analyst}@mock_data_db:5432/${MOCK_DB_NAME:-financial_crime}"
echo ""
echo " To stop:  $COMPOSE down"
echo " To reset: $COMPOSE down -v  (also removes data volumes)"
echo ""
