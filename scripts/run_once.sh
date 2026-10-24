#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
exec >> logs/pipeline.log 2>&1
printf '\nMobiliteIQ %s\n' "$(date -Is)"
.venv/bin/python -m mobiliteiq run
# Le premier entraînement reste une action explicite, après vérification de l'historique.
if [ -n "$(find models/mobiliteiq -name '*.joblib' -print -quit 2>/dev/null || true)" ]; then
  .venv/bin/python -m mobiliteiq score
fi
