# Swarm-to-Dashboard Integration

The swarm emits the complete canonical bundle to a dashboard ingestion endpoint. The integration does not require GitHub or Neo4j.

| Environment variable | Purpose |
|---|---|
| `DASHBOARD_INGEST_URL` | Full HTTPS endpoint for production run-bundle ingestion. |
| `DASHBOARD_INGEST_TOKEN` | Dedicated bearer secret shared only by the swarm process and dashboard server. |
| `DASHBOARD_INGEST_TIMEOUT_SECONDS` | Optional request timeout; defaults to 30 seconds. |

The emitter always writes the bundle locally before attempting network submission. It retries a failed network delivery three times, records the terminal delivery error in the run directory, and does not replace, alter, or synthesize findings. Re-submitting the same valid bundle is safe because ingestion is idempotent by run ID.

The dashboard rejects non-production mode, unsupported schema versions, inconsistent nested run IDs, fallback source flags, mock finding flags, simulated finding flags, and fallback finding flags.

## Launch sequence

1. Publish the dashboard and retain its HTTPS origin.
2. Set `DASHBOARD_INGEST_URL` to `<origin>/api/ingest/v1/runs` in the swarm runtime.
3. Set the same 32-character-or-longer `DASHBOARD_INGEST_TOKEN` in both runtimes.
4. Optionally set `SWARM_CODE_VERSION` to the deployed release or commit.
5. Verify `<origin>/api/ingest/v1/health` with the bearer token.
6. Launch `python3 run_live_swarm.py` from the repository root.
7. Confirm `reports/live_runs/<run_id>/dashboard_bundle.json` exists.
8. Open the authenticated dashboard and select the emitted `runId`.

## Lifecycle contract

The orchestrator emits the same `runId` repeatedly as the run changes from `starting` to `running` and then to `completed`, `partial`, or `failed`. Each update contains all currently accepted stage, source, finding, investigation, report, and error records. The dashboard replaces only swarm-owned run data; analyst decisions are append-only and remain separate.

No GitHub or Neo4j connection is required. Neo4j may still serve internal swarm workflows, but it is not a dashboard dependency.
