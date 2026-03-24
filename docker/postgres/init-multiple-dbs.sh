#!/bin/bash
# Creates multiple PostgreSQL databases in one container init pass.
# Referenced by docker-compose postgres service.
set -e

function create_database() {
    local database=$1
    echo "  Creating database '$database' …"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE $database;
EOSQL
}

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
    for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
        create_database $db
    done
    echo "Multiple databases created."
fi
