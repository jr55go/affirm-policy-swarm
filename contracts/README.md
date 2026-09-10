# Dashboard Run Contract

The dashboard is an independent system. It does not require GitHub or Neo4j. The swarm is the producer and the dashboard is the durable consumer.

Every production run emits a versioned `Swarm Run Bundle` with the run state, pipeline stages, source health, validated findings, investigation threads, report content, and errors. The producer may submit the bundle repeatedly during a run; ingestion is idempotent by `run.id` and replaces only records belonging to that run.

The dashboard accepts only `run.mode = "production"`. It rejects any source marked `usedFallback = true` and any finding whose provenance marks `isFallback`, `isMock`, or `isSimulated`. Test, golden, smoke, audit, recovery, and training files are not ingestion sources.

The required producer configuration is `DASHBOARD_INGEST_URL` and `DASHBOARD_INGEST_TOKEN`. If either is absent, the swarm still writes the bundle locally to `reports/live_runs/<run_id>/dashboard_bundle.json`; submission failure must not erase the local bundle or change source findings.

Dashboard pages derive only from ingested records. Before the first successful production ingestion, the product displays an explicit empty state rather than example metrics or findings.
