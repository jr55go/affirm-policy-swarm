#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

dashboard_origin="${1:-${DASHBOARD_ORIGIN:-}}"
if [[ -n "$dashboard_origin" ]]; then
  export DASHBOARD_INGEST_URL="${dashboard_origin%/}/api/ingest/v1/runs"
elif [[ -z "${DASHBOARD_INGEST_URL:-}" ]]; then
  echo "Usage: $0 https://YOUR-PUBLISHED-DASHBOARD-DOMAIN" >&2
  echo "Alternatively set DASHBOARD_INGEST_URL in .env." >&2
  exit 1
fi

if [[ -z "${DASHBOARD_INGEST_TOKEN:-}" ]]; then
  read -r -s -p "Dashboard ingestion token: " DASHBOARD_INGEST_TOKEN
  echo
  export DASHBOARD_INGEST_TOKEN
fi

if (( ${#DASHBOARD_INGEST_TOKEN} < 32 )); then
  echo "DASHBOARD_INGEST_TOKEN must be at least 32 characters." >&2
  exit 1
fi

export DASHBOARD_INGEST_TIMEOUT_SECONDS="${DASHBOARD_INGEST_TIMEOUT_SECONDS:-30}"
export SWARM_CODE_VERSION="${SWARM_CODE_VERSION:-$(git rev-parse HEAD 2>/dev/null || echo unversioned-runtime)}"

command -v python3 >/dev/null || { echo "python3 is required." >&2; exit 1; }
command -v ollama >/dev/null || { echo "ollama is required." >&2; exit 1; }

python3 scripts/verify_dashboard_connection.py

if ! curl -fsS http://localhost:11434/api/tags >/dev/null; then
  echo "Ollama is not reachable at http://localhost:11434." >&2
  echo "Start it with: ollama serve" >&2
  exit 1
fi

required_models=("nemotron:70b" "qwen" "qwen2.5-coder:32b" "llama3.2:latest")
missing_models=()
installed_models="$(ollama list 2>/dev/null | awk 'NR > 1 {print $1}')"
for model in "${required_models[@]}"; do
  if ! grep -Fxq "$model" <<<"$installed_models" && ! grep -Fxq "${model}:latest" <<<"$installed_models"; then
    missing_models+=("$model")
  fi
done

if (( ${#missing_models[@]} )); then
  echo "Required Ollama models are missing:" >&2
  printf '  ollama pull %s\n' "${missing_models[@]}" >&2
  exit 1
fi

if [[ -z "${CONGRESS_GOV_API_KEY:-}" ]]; then
  echo "CONGRESS_GOV_API_KEY is required by run_live_swarm.py." >&2
  exit 1
fi

echo "Starting production swarm; dashboard endpoint verified."
exec python3 run_live_swarm.py
