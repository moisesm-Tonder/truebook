#!/bin/bash
set -e

echo "=== AFinOps Tonder Backend ==="
echo "1. Corriendo migraciones..."
alembic upgrade head

echo "2. Creando usuario admin..."
python seed.py

echo "3. Iniciando servidor..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
