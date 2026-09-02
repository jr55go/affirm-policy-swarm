import os
import json
import logging
import hashlib
from datetime import datetime
from neo4j import GraphDatabase

class InvestigationMemory:
    """
    Persistent Analyst's Notebook with File-Backed Storage & Temporal Memory.
    Tracks Knowns, Unknowns, Conflicts, Watch Targets, and Scheduled Follow-Up Dates.
    """
    def __init__(self, storage_path="notebook.json", uri=None, user=None, password=None):
        self.storage_path = os.path.expanduser(f"~/.openclaw/workspace/affirm_policy_swarm/{storage_path}")
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        except Exception:
            self.driver = None

    def get_analyst_notebook(self):
        """Fetches active policy threads and temporal watch targets."""
        # 1. Try file-backed storage first
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    notebook = json.load(f)
                    logging.info(f"[InvestigationMemory] 📖 Loaded {len(notebook)} threads from {self.storage_path}")
                    return notebook
            except Exception as e:
                logging.warning(f"[InvestigationMemory] Error reading {self.storage_path}: {e}")

        # 2. Neo4j fallback
        if self.driver:
            query = """
            MATCH (i:Investigation) WHERE i.status IN ['ACTIVE', 'MONITOR']
            OPTIONAL MATCH (i)-[:HAS_KNOWN]->(k:KnownFact)
            OPTIONAL MATCH (i)-[:HAS_UNKNOWN]->(u:UnknownGap)
            RETURN i.id AS inv_id, i.topic AS topic,
                   collect(DISTINCT k.text) AS knowns,
                   collect(DISTINCT u.text) AS unknowns
            """
            try:
                with self.driver.session() as session:
                    res = session.run(query)
                    return [rec.data() for rec in res]
            except Exception:
                pass

        return []

    def save_analyst_notebook(self, updated_threads):
        """Saves active policy threads and temporal triggers directly to disk."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(updated_threads, f, indent=2)
            logging.info(f"[InvestigationMemory] 💾 Saved {len(updated_threads)} policy threads & temporal memory to {self.storage_path}")
        except Exception as e:
            logging.error(f"[InvestigationMemory] Failed to save notebook to disk: {e}")

    def log_document_visit(self, url, title, document_hash, reason_read):
        pass
