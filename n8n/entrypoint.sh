#!/bin/sh
set -e

echo "[n8n-init] Importing pre-configured OpenAI credentials..."
n8n import:credentials --input=/workflow/credentials.json || true

echo "[n8n-init] Importing Invoice Extraction workflow..."
n8n import:workflow --input=/workflow/workflow.json || true

echo "[n8n-init] Activating Invoice Extraction workflow..."
n8n publish:workflow --id=1axMBaO7or9ssM1U || n8n update:workflow --id=1axMBaO7or9ssM1U --active=true || true

echo "[n8n-init] Initialization complete. Starting n8n server..."
exec /docker-entrypoint.sh "$@"
