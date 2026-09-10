# Connect a Local DGX Spark Swarm to the Dashboard

## Architecture

The DGX Spark remains the producer and compute host. The published dashboard is the authenticated consumer and durable display layer.

```text
DGX Spark agents and local Ollama
        |
        | canonical version 1.0.0 run bundle over outbound HTTPS
        v
POST /api/ingest/v1/runs
        |
        v
Dashboard database -> authenticated Overview, Review, Investigations, Reports
```

The dashboard never opens a connection back to the DGX Spark. No inbound firewall rule, public DGX address, VPN, GitHub synchronization, or Neo4j exposure is required. The DGX only needs outbound HTTPS access to the published dashboard.

## 1. Publish and configure the dashboard

Open the latest dashboard checkpoint shared in Manus. In **Settings → Secrets**, set `SWARM_INGEST_TOKEN` to a random value of at least 32 characters. Generate one on the DGX Spark if needed:

```bash
openssl rand -hex 32
```

Paste the same value into the dashboard secret and the DGX environment. Publish the dashboard, then copy its stable HTTPS origin, such as `https://YOUR-NAME.manus.space`. Do not use the temporary development-preview address for ongoing swarm runs.

## 2. Update the local swarm code

From the repository directory on the DGX Spark, first inspect local work:

```bash
cd /path/to/affirm-policy-swarm
git status
```

If the working tree is clean and the local branch has no DGX-only commits, fast-forward it:

```bash
git fetch origin
git merge --ff-only origin/main
```

If the DGX has uncommitted changes or local commits, create a safety branch and review what will be committed before merging:

```bash
git switch -c "dgx-safety-before-dashboard-$(date +%Y%m%d-%H%M%S)"
git status --short
git add -u
# Add only intended untracked source files by explicit path; never add .env.
# git add path/to/intended-new-source-file
git diff --cached
git commit -m "Checkpoint DGX swarm before dashboard integration"
git fetch origin
git merge origin/main
```

Resolve merge conflicts rather than discarding DGX-specific work. The integration spans commits `c81562a` and `a6e2090`, including multiple production agents, the emitter, contract, launcher, tests, and helper scripts. Merge the commits as a unit; do not copy only four named files. In particular, preserve `scripts/run_swarm_with_dashboard.sh` and `scripts/verify_dashboard_connection.py`, because later commands use them.

## 3. Configure the DGX environment

Copy `.env.example` to `.env` only if the repository does not already have an environment file. Do not overwrite working credentials.

```bash
test -f .env || cp .env.example .env
chmod 600 .env
```

Edit `.env` and set these values:

```dotenv
CONGRESS_GOV_API_KEY=YOUR_EXISTING_KEY
LEGISCAN_API_KEY=YOUR_EXISTING_KEY
REGULATIONS_GOV_API_KEY=YOUR_EXISTING_KEY

DASHBOARD_INGEST_URL=https://YOUR-PUBLISHED-DASHBOARD-DOMAIN/api/ingest/v1/runs
DASHBOARD_INGEST_TOKEN=THE_EXACT_SECRET_SET_IN_DASHBOARD_SETTINGS
DASHBOARD_INGEST_TIMEOUT_SECONDS=30
# Leave blank to let the wrapper record `git rev-parse HEAD`, or set an actual release/commit.
SWARM_CODE_VERSION=
```

The only required source credential enforced by the launcher is `CONGRESS_GOV_API_KEY`. Missing optional source credentials produce failed or skipped source states; they do not produce sample data.

## 4. Verify local runtime prerequisites

The active production agents call the local Ollama API at `http://localhost:11434` and currently require these model names:

```bash
ollama pull nemotron:70b
ollama pull qwen
ollama pull qwen2.5-coder:32b
ollama pull llama3.2:latest
```

Confirm Ollama is available:

```bash
curl -fsS http://localhost:11434/api/tags >/dev/null && echo "Ollama ready"
```

Use the Python environment that already launches the local swarm. The new emitter and health verifier use the Python standard library, but the full existing swarm does not: `run_live_swarm.py` imports `python-dotenv`, and active agents use packages such as `requests`, `feedparser`, `beautifulsoup4`, `pandas`, and the Neo4j driver. This repository currently has no authoritative lockfile or requirements manifest, so these directions are for the already-working DGX environment, not a fresh Python bootstrap.

## 5. Verify the dashboard connection without sending data

Load the environment and run the included health verifier:

```bash
set -a
source .env
set +a
python3 scripts/verify_dashboard_connection.py
```

A correct connection prints the dashboard origin and `Accepted schema version: 1.0.0`. HTTP 401 means the two token values differ. A timeout or name-resolution error means the DGX cannot reach the published HTTPS origin.

This verifier has been exercised successfully against the dashboard ingestion health route. It performs a read-only authenticated health request and never submits a run bundle.

## 6. Launch the first connected production run

The wrapper performs the endpoint check, verifies Ollama and the four model names, checks the required Congress.gov key, records the current Git commit as the code version, and starts the existing production launcher:

```bash
chmod +x scripts/run_swarm_with_dashboard.sh
./scripts/run_swarm_with_dashboard.sh https://YOUR-PUBLISHED-DASHBOARD-DOMAIN
```

If the endpoint and token are already stored in `.env`, the origin argument is optional:

```bash
./scripts/run_swarm_with_dashboard.sh
```

## 7. Verify local and dashboard output

The run creates a directory like `reports/live_runs/run_1789000000/`. During execution, confirm the canonical bundle exists:

```bash
latest_run="$(find reports/live_runs -mindepth 1 -maxdepth 1 -type d -name 'run_*' | sort | tail -1)"
echo "$latest_run"
python3 -m json.tool "$latest_run/dashboard_bundle.json" >/dev/null && echo "Bundle JSON valid"
```

Open the published dashboard and sign in. The run selector should show the same `run_*` identifier. **Overview** displays run and source status, **Review inbox** displays only accepted validated findings, **Investigations** displays threads derived from those findings, and **Reports** displays the exact emitted Markdown report.

## 8. Delivery failures and safe retry

The emitter always writes `dashboard_bundle.json` locally before submission. It retries network delivery three times. A terminal delivery failure creates `dashboard_delivery_error.json` in the run directory and does not invent findings.

After correcting connectivity or the token, resubmit the saved bundle with:

```bash
set -a; source .env; set +a
latest_run="$(find reports/live_runs -mindepth 1 -maxdepth 1 -type d -name 'run_*' | sort | tail -1)"
test -n "$latest_run" && test -f "$latest_run/dashboard_bundle.json"
curl --fail-with-body \
  -H "Authorization: Bearer $DASHBOARD_INGEST_TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary "@$latest_run/dashboard_bundle.json" \
  "$DASHBOARD_INGEST_URL"
```

Submitting the identical bundle again is idempotent. The dashboard replaces swarm-owned rows for that run and does not duplicate them; analyst review history is stored separately.
