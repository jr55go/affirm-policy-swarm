# Production Runtime Boundary

The dashboard-producing runtime consists of `run_live_swarm.py`, `agents/orchestrator.py`, the active modules imported by that orchestrator, `infrastructure/dashboard_emitter.py`, and the canonical schema under `contracts/`.

| Included in dashboard output | Excluded from dashboard output |
|---|---|
| Records fetched during the current production run | `data/fine_tuning/golden_dataset.jsonl` |
| Findings that pass the validation agent without a fallback marker | Root Markdown report snapshots and audit documents |
| Source health and stage results from the current run | Repair scripts, patch utilities, backups, baselines, and historical copies |
| The exact report generated for the current run | Hard-coded run IDs from old dashboard or verification scripts |
| Investigation threads deterministically derived from accepted findings | Mock, simulated, demo, dummy, search-fallback, or analysis-fallback records |

The emitter is the final production boundary. It rejects explicitly unsafe source records, excludes fallback-derived or unvalidated findings, and writes the versioned run bundle atomically before submitting it. A missing source or credential produces no substitute intelligence.

The repository still contains legacy utilities and historical artifacts for recovery and audit purposes. They are not imported by the production launcher and are not read by the emitter. The production compile and tests target the runtime boundary described above.
