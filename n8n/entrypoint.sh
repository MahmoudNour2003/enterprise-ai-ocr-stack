#!/bin/sh
set -e

echo "[n8n-init] Importing pre-configured OpenAI credentials..."
n8n import:credentials --input=/workflow/credentials.json || true

echo "[n8n-init] Importing Invoice Extraction workflow..."
n8n import:workflow --input=/workflow/workflow.json || true

echo "[n8n-init] Activating workflow..."
n8n update:workflow --all --active=true || true
n8n publish:workflow --all || true

echo "[n8n-init] Initialization complete. Starting n8n server..."
exec /docker-entrypoint.sh "$@"
