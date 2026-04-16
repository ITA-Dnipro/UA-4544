#!/bin/sh

set -e

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}"; do
  sleep 1
done
echo " PostgreSQL is ready."

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting Django development server on 0.0.0.0:8000..."
exec python manage.py runserver 0.0.0.0:8000
