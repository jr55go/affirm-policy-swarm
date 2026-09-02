import os
import logging
from neo4j import GraphDatabase

class GraphConnector:
    def __init__(self, uri=None, user=None, password=None):
        """
        Initialize the Neo4j connection.
        Parameters can be passed directly or read from environment variables.
        Environment variables: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test the connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logging.info(f"[GraphConnector] Connected to Neo4j at {self.uri}")
        except Exception as e:
            logging.error(f"[GraphConnector] Failed to connect to Neo4j: {e}")
            # We don't raise here because we want the swarm to continue even if DB is down
            self.driver = None

    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logging.info("[GraphConnector] Connection closed.")

    def get_active_investigations(self, limit=10):
        """
        Retrieves active policy threads, recent observations, and key entities 
        from Neo4j to serve as the system's persistent memory state.
        """
        if not self.driver:
            return []

        query = """
        MATCH (p:PolicyRecord)
        OPTIONAL MATCH (p)-[:HAS_OBSERVATION]->(o:Observation)
        OPTIONAL MATCH (p)-[:RELATES_TO]->(t:Theme)
        OPTIONAL MATCH (p)-[:MENTIONS]->(e)
        RETURN p.title AS title, 
               p.jurisdiction AS jurisdiction, 
               p.impact_score AS impact_score, 
               p.compressed_summary AS summary,
               collect(DISTINCT t.name) AS themes,
               collect(DISTINCT e.name) AS entities,
               max(o.timestamp) AS last_updated
        ORDER BY last_updated DESC LIMIT $limit
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, limit=limit)
                return [record.data() for record in result]
        except Exception as e:
            logging.error(f"[GraphConnector] Failed to retrieve active investigations: {e}")
            return []

    def sync_findings(self, findings, run_id=None):
        """
        Sync validated findings to the Neo4j graph database with temporal versioning.
        Maintains the current state in PolicyRecord nodes and creates Observation nodes
        for historical tracking.
        Also extracts and links entities (organizations, policymakers, themes).

        :param findings: List of validated finding dictionaries (each with at least: title, text_context, jurisdiction, impact_score, analysis, validation_status, compressed_summary, entities)
        :param run_id: Unique identifier for this run (used for Observation nodes)
        """
        if not self.driver:
            logging.warning("[GraphConnector] No database connection. Skipping sync.")
            return

        if run_id is None:
            # Generate a run_id if not provided
            import time
            run_id = f"run_{int(time.time())}"

        with self.driver.session() as session:
            for finding in findings:
                try:
                    # Extract relevant fields
                    title = finding.get("title", "Untitled")
                    context = finding.get("text_context", "")
                    jurisdiction_name = finding.get("jurisdiction", "Unknown")
                    # The 'source' field is set by the monitoring agents (e.g., RegulatoryWatchAgent, ResearchMonitorAgent)
                    source_name = finding.get("source", "Unknown Source")
                    impact_score = finding.get("impact_score", "low")
                    analysis = finding.get("analysis", "")
                    validation_status = finding.get("validation_status", "not_required")
                    compressed_summary = finding.get("compressed_summary", "")
                    entities = finding.get("entities", {"organizations": [], "policymakers": [], "themes": []})

                    # Use a single transaction to handle all operations for this finding
                    def add_finding_tx(tx):
                        # Merge Jurisdiction node
                        tx.run("""
                        MERGE (j:Jurisdiction {name: $jurisdiction_name})
                        """, jurisdiction_name=jurisdiction_name)

                        # Merge Source node
                        tx.run("""
                        MERGE (s:Source {name: $source_name})
                        """, source_name=source_name)

                        # Merge PolicyRecord node by title and jurisdiction (composite key for uniqueness)
                        tx.run("""
                        MERGE (p:PolicyRecord {title: $title, jurisdiction: $jurisdiction_name})
                        """, title=title, jurisdiction_name=jurisdiction_name)

                        # Update the PolicyRecord with current state (so it always reflects the latest)
                        tx.run("""
                        MATCH (p:PolicyRecord {title: $title, jurisdiction: $jurisdiction_name})
                        SET p.context = $context,
                            p.analysis = $analysis,
                            p.impact_score = $impact_score,
                            p.validation_status = $validation_status,
                            p.compressed_summary = $compressed_summary
                        """, title=title, jurisdiction_name=jurisdiction_name,
                             context=context, impact_score=impact_score,
                             analysis=analysis, validation_status=validation_status,
                             compressed_summary=compressed_summary)

                        # Link PolicyRecord to Jurisdiction (create if not exists)
                        tx.run("""
                        MATCH (p:PolicyRecord {title: $title, jurisdiction: $jurisdiction_name})
                        MATCH (j:Jurisdiction {name: $jurisdiction_name})
                        MERGE (p)-[:GOVERNED_BY]->(j)
                        """, title=title, jurisdiction_name=jurisdiction_name)

                        # Link PolicyRecord to Source (create if not exists)
                        tx.run("""
                        MATCH (p:PolicyRecord {title: $title, jurisdiction: $jurisdiction_name})
                        MATCH (s:Source {name: $source_name})
                        MERGE (p)-[:SOURCE]->(s)
                        """, title=title, jurisdiction_name=jurisdiction_name, source_name=source_name)

                        # Create an Observation node for this run, containing the state at this point in time
                        tx.run("""
                        MATCH (p:PolicyRecord {title: $title, jurisdiction: $jurisdiction_name})
                        CREATE (o:Observation {
                            run_id: $run_id,
                            timestamp: datetime(),
                            impact_score: $impact_score,
                            validation_status: $validation_status,
                            compressed_summary: $compressed_summary
                        })
                        MERGE (p)-[:HAS_OBSERVATION]->(o)
                        """, title=title, jurisdiction_name=jurisdiction_name,
                             run_id=run_id, impact_score=impact_score,
                             validation_status=validation_status,
                             compressed_summary=compressed_summary)

                        # --- Entity Linking ---
                        # Organizations
                        for org_name in entities.get("organizations", []):
                            if org_name and org_name.strip():
                                tx.run("""
                                MERGE (o:Organization {name: $org_name})
                                WITH o
                                MATCH (p:PolicyRecord {title: $title, jurisdiction: $jurisdiction_name})
                                MERGE (p)-[:MENTIONS]->(o)
                                """, org_name=org_name.strip(), title=title, jurisdiction_name=jurisdiction_name)

                        # Policymakers
                        for person_name in entities.get("policymakers", []):
                            if person_name and person_name.strip():
                                tx.run("""
                                MERGE (p:Policymaker {name: $person_name})
                                WITH p
                                MATCH (pr:PolicyRecord {title: $title, jurisdiction: $jurisdiction_name})
                                MERGE (pr)-[:MENTIONS]->(p)
                                """, person_name=person_name.strip(), title=title, jurisdiction_name=jurisdiction_name)

                        # Themes
                        for theme in entities.get("themes", []):
                            if theme and theme.strip():
                                tx.run("""
                                MERGE (t:Theme {name: $theme})
                                MERGE (pr:PolicyRecord {title: $title, jurisdiction: $jurisdiction_name})
                                MERGE (pr)-[:RELATES_TO]->(t)
                                """, theme=theme.strip(), title=title, jurisdiction_name=jurisdiction_name)

                    # Execute the transaction
                    session.execute_write(add_finding_tx)

                except Exception as e:
                    logging.error(f"[GraphConnector] Error processing finding '{title}': {e}")
                    # Continue with the next finding
                    continue

            logging.info(f"[GraphConnector] Successfully synced {len(findings)} findings to Neo4j with temporal versioning and entity linking (run_id: {run_id}).")