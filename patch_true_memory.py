import os
import shutil

discovery_path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents/discovery_agent.py")

# Create a backup just in case
shutil.copy2(discovery_path, discovery_path + ".before_true_memory")

with open(discovery_path, "r", encoding="utf-8") as f:
    discovery_code = f.read()

old_execute = """    def execute_task(self, task_data):
        queries = task_data.get("queries", [])
        records = []

        clusters = [
            " site:consumerfinance.gov",
            " site:dfs.ny.gov",
            " site:americanbanker.com",
        ]

        for q in queries:
            base_kw = " ".join(q.split()[:6])
            for cluster in clusters:
                target_query = f"{base_kw}{cluster}"
                logging.info(f"[{self.agent_id}] Vectoring Search: {target_query}")
                
                time.sleep(random.uniform(2.0, 4.0))
                search_hits = self.perform_search(target_query)
                
                for r in search_hits:
                    score = self.gatekeeper_check(q, r["snippet"])
                    if score >= 6:
                        logging.info(f"[{self.agent_id}] Target Acquired! (Score: {score}) -> {r['url']}")
                        r["relevance_score"] = score
                        records.append(r)
                    else:
                        logging.info(f"[{self.agent_id}] Target Discarded (Score: {score}) -> {r['url']}")

        logging.info(f"[{self.agent_id}] Discovery complete. Acquired {len(records)} verified records.")
        return {"records": records}"""

new_execute = """    def execute_task(self, task_data):
        queries = task_data.get("queries", [])
        records = []

        # 1. Load True System Memory (Evidence Ledger)
        import os, json
        seen_urls = set()
        ledger_path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/reports/evidence_ledger.json")
        if os.path.exists(ledger_path):
            try:
                with open(ledger_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "live_evaluation_ledger" in data:
                        seen_urls = {item.get("url") for item in data["live_evaluation_ledger"] if item.get("url")}
            except Exception as e:
                logging.error(f"[{self.agent_id}] Failed to read evidence ledger: {e}")

        clusters = [
            " site:consumerfinance.gov",
            " site:dfs.ny.gov",
            " site:americanbanker.com",
        ]

        for q in queries:
            base_kw = " ".join(q.split()[:6])
            for cluster in clusters:
                target_query = f"{base_kw}{cluster}"
                logging.info(f"[{self.agent_id}] Vectoring Search: {target_query}")
                
                time.sleep(random.uniform(2.0, 4.0))
                search_hits = self.perform_search(target_query)
                
                for r in search_hits:
                    url = r["url"]
                    
                    # 2. Enforce Memory Gatekeeper Check
                    if url in seen_urls:
                        logging.info(f"[{self.agent_id}] Memory Gatekeeper: Skipping {url} (Already in Ledger)")
                        continue

                    score = self.gatekeeper_check(q, r["snippet"])
                    if score >= 6:
                        logging.info(f"[{self.agent_id}] Target Acquired! (Score: {score}) -> {url}")
                        r["relevance_score"] = score
                        records.append(r)
                        # Add to seen immediately so we don't grab it again in the next query loop
                        seen_urls.add(url)
                    else:
                        logging.info(f"[{self.agent_id}] Target Discarded (Score: {score}) -> {url}")

        logging.info(f"[{self.agent_id}] Discovery complete. Acquired {len(records)} NEW verified records.")
        return {"records": records}"""

discovery_code = discovery_code.replace(old_execute, new_execute)

with open(discovery_path, "w", encoding="utf-8") as f:
    f.write(discovery_code)

print("✅ DiscoveryAgent perfectly wired to the master evidence_ledger.json.")
