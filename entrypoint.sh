#!/bin/sh
set -e

export FLASK_APP=app:app

echo "==> Aguardando banco de dados..."
python -m deploy.wait_db

echo "==> Aplicando migrations..."
flask db upgrade

echo "==> Bootstrap do primeiro usuário (se configurado)..."
python -m deploy.bootstrap

echo "==> Iniciando Gunicorn na porta ${PORT:-8000}..."
exec gunicorn app:app \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --threads "${WEB_THREADS:-4}" \
  --timeout "${WEB_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
