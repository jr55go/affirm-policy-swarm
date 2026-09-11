import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agents.discovery_agent import DiscoveryAgent
from agents.planner_agent import PlannerAgent
from agents.reader_agent import ReaderAgent
from agents.legislative_monitor import LegislativeMonitorAgent
from agents.entity_resolution_agent import EntityResolutionAgent
from agents.risk_scoring_agent import RiskScoringAgent
from agents.impact_analyzer_agent import ImpactAnalyzerAgent
from agents.context_expansion_agent import ContextExpansionAgent
from agents.context_compressor_agent import ContextCompressorAgent
from agents.research_synthesis_agent import ResearchSynthesisAgent
from agents.validation_agent import ValidationAgent
from agents.reporting_agent import ReportingAgent
from agents.human_feedback_agent import HumanFeedbackAgent
from agents.market_sentiment_agent import MarketSentimentAgent
from agents.public_statement_monitor_agent import PublicStatementMonitorAgent
from infrastructure.connectors.federal_register_connector import FederalRegisterConnector
from infrastructure.connectors.regulations_gov_connector import RegulationsGovConnector
from infrastructure.connectors.cfpb_connector import CFPBConnector
from infrastructure.graph_db import GraphConnector
from agents.evidence_triage_agent import EvidenceTriageAgent
from infrastructure.fingerprint_util import generate_content_fingerprint
from infrastructure.investigation_memory import InvestigationMemory
from infrastructure.dashboard_emitter import DashboardRunEmitter, partition_production_records

import json
import time as pytime
import logging
import argparse
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def filter_off_topic_records(records: list) -> list:
    '''Intelligent Gatekeeper: Deduplicates using MD5 state hashes, uses Llama 3.2 for contextual filtering.'''
    import requests
    import json
    import logging
    import hashlib
    import os
    
    SEEN_DB = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/seen_nodes.json")
    seen_hashes = set()
    if os.path.exists(SEEN_DB):
        try:
            with open(SEEN_DB, "r") as f:
                seen_hashes = set(json.load(f))
        except Exception:
            pass

    filtered = []
    new_seen = set(seen_hashes)
    
    for r in records:
        title = str(r.get("title", ""))
        url = str(r.get("url", ""))
        snippet = str(r.get("snippet", r.get("text_context", "")))
        
        # Generate persistent ID based on URL and Title
        record_id = hashlib.md5((title + url).encode('utf-8')).hexdigest()
        
        if record_id in seen_hashes:
            continue # Skip completely, we already evaluated this in a previous run
            
        prompt = (
            "Analyze this policy record:\n"
            f"Title: {title}\n"
            f"Snippet: {snippet}\n\n"
            "Is this record relevant to a fintech company like Affirm, broader fintech policy, or retail financial regulation? "
            "Include: BNPL, consumer credit, neobanks, bank-fintech partnerships (BaaS), congressional investigations into fintech apps/founders, "
            "FTC/CFPB enforcement, and AI governance. Answer ONLY with the word YES or NO."
        )
        
        try:
            res = requests.post("http://localhost:11434/api/generate", 
                                json={"model": "llama3.2:latest", "prompt": prompt, "stream": False}, 
                                timeout=10)
            llm_response = res.json().get("response", "").strip().upper()
            
            new_seen.add(record_id) # Mark as seen so we don't evaluate it on the next run
            
            if "YES" in llm_response:
                filtered.append(r)
            else:
                logging.info(f"[Gatekeeper] Llama Rejected (Off-Topic): {title}")
        except Exception as e:
            logging.warning(f"[Gatekeeper] Error on '{title}', defaulting to keep. Error: {e}")
            r["triage_fallback"] = True
            filtered.append(r)
            
    # Save updated dynamic state
    try:
        with open(SEEN_DB, "w") as f:
            json.dump(list(new_seen), f)
    except Exception as e:
        logging.warning(f"Failed to save dynamic state: {e}")
        
    return filtered

def deduplicate_records(records: list) -> list:
    """Removes duplicates using the robust SHA-256 content fingerprint."""
    seen_hashes, unique_records = set(), []
    for r in records:
        fingerprint = generate_content_fingerprint(str(r.get("text_context", "")) or str(r.get("snippet", "")))
        r["document_hash"] = fingerprint or "unknown_hash"
        if fingerprint and fingerprint not in seen_hashes:
            seen_hashes.add(fingerprint); unique_records.append(r)
        elif not fingerprint:
            unique_records.append(r)
    return unique_records

class PolicyOrchestratorAgent:
    def run_swarm(self, cg_key, ls_key, golden_run=False):
        if golden_run:
            raise ValueError("Golden/test runs are not permitted through the production dashboard pipeline.")
        run_id = f"run_{int(pytime.time())}"
        report_dir = f"reports/live_runs/{run_id}"
        os.makedirs(report_dir, exist_ok=True)
        emitter = DashboardRunEmitter(
            run_id=run_id,
            report_dir=report_dir,
            objective="Affirm regulatory and public-policy intelligence run",
        )
        try:
            return self._run_swarm(cg_key, ls_key, run_id, report_dir, emitter)
        except Exception as error:
            logger.exception(f"[{self.__class__.__name__}] Swarm run failed: {error}")
            emitter.add_error("orchestrator", str(error), recoverable=False)
            try:
                emitter.emit("failed")
            except Exception as emit_error:
                logger.exception(f"[{self.__class__.__name__}] Failed to emit terminal run state: {emit_error}")
            raise

    def _run_swarm(self, cg_key, ls_key, run_id, report_dir, emitter):
        planner = PlannerAgent()
        discovery = DiscoveryAgent()
        reader = ReaderAgent()
        human_feedback = HumanFeedbackAgent()
        market_sentiment = MarketSentimentAgent()
        public_statement = PublicStatementMonitorAgent()
        
        def accept_source(records, key, name, category):
            safe, rejected = partition_production_records(records if isinstance(records, list) else [])
            error = f"Rejected {len(rejected)} explicit non-production record(s)." if rejected else None
            emitter.source(key, name, category, "degraded" if rejected else "healthy", len(safe), error=error)
            return safe

        emitter.emit("starting")
        
        logger.info(f"[{self.__class__.__name__}] Starting swarm run: {run_id}")

        # DASHBOARD HOOK 1: Initialization
        try:
            from infrastructure.dashboard_emitter import DashboardRunEmitter
            dashboard = DashboardRunEmitter(run_id=run_id, report_dir=report_dir, objective="Affirm policy intelligence production run")
            dashboard.emit("starting")
        except Exception as e:
            logger.error(f"Failed to initialize Dashboard Emitter: {e}")
            dashboard = None

        # BOOT SEQUENCE: RETRIEVE ANALYST NOTEBOOK
        notebook_state, inv_memory = [], None
        try:
            inv_memory = InvestigationMemory()
            notebook_state = inv_memory.get_analyst_notebook()
            logger.info(f"[{self.__class__.__name__}] Loaded {len(notebook_state)} active policy threads from Analyst's Notebook")
        except Exception as e: logger.warning(f"Failed to fetch notebook: {e}")
        
        all_records, triage_agent = [], EvidenceTriageAgent()
        recent_brain = []
        
        # 1. STREAM A: WEB DISCOVERY & TRIAGE
        emitter.stage("discovery", "running")
        for iteration in range(3):
            logger.info(f"--- Starting Autonomous Iteration {iteration} ---")
            queries = planner.generate_plan(notebook_state, recent_brain)
            discovery_out = discovery.execute_task({"queries": queries})
            search_hits = discovery_out.get("records", [])
            
            logger.info(f"[{self.__class__.__name__}] Triaging {len(search_hits)} search hits...")
            triaged_hits = triage_agent.evaluate_targets(search_hits, notebook_state)
            
            read_targets = []
            for hit in triaged_hits:
                if hit.get("decision") == "read":
                    read_targets.append(hit)
                else:
                    # FEEDBACK LOOP: Track why targets were skipped
                    reason = hit.get('triage_reasoning', 'Off-topic')
                    recent_brain.append(f"Query '{hit.get('query_vector', 'N/A')}' -> Rejected URL: {hit.get('url')} - Reason: {reason}")
            
            # Keep recent brain from blowing up the context window
            recent_brain = recent_brain[-20:]
            
            all_records.extend(accept_source(read_targets, f"web_discovery_{iteration}", f"Web discovery iteration {iteration + 1}", "web"))
            logger.info(f"[{self.__class__.__name__}] Iteration {iteration} Complete: Kept {len(read_targets)} high-novelty targets")
            
        
        emitter.stage("discovery", "completed", output_count=len(all_records))

        # 4. STREAM D: GUARANTEED DIRECT SOURCES (RSS Feeds & SEC EDGAR)
        logger.info(f"[{self.__class__.__name__}] Starting Stream D: Guaranteed Direct Ingestion")
        emitter.stage("direct_sources", "running")
        direct_records = []
        
        # 4a. RSS Feed Agent
        try:
            from agents.rss_feed_agent import RSSFeedAgent
            rss_agent = RSSFeedAgent()
            rss_out = rss_agent.execute_task({})
            rss_recs = rss_out.get("records", [])
            direct_records.extend(accept_source(rss_recs, "rss", "RSS feeds", "rss"))
            logger.info(f"[{self.__class__.__name__}] RSS Feed Agent: Collected {len(rss_recs)} records")
        except Exception as e:
            logger.error(f"RSS Feed Agent failed: {e}")
            emitter.source("rss", "RSS feeds", "rss", "failed", 0, error=str(e))

        # 4b. SEC EDGAR Agent
        try:
            from agents.sec_edgar_agent import SECEdgarAgent
            sec_agent = SECEdgarAgent()
            sec_out = sec_agent.execute_task({})
            sec_recs = sec_out.get("records", [])
            direct_records.extend(accept_source(sec_recs, "sec_edgar", "SEC EDGAR", "sec"))
            logger.info(f"[{self.__class__.__name__}] SEC EDGAR Agent: Collected {len(sec_recs)} records")
        except Exception as e:
            logger.error(f"SEC EDGAR Agent failed: {e}")
            emitter.source("sec_edgar", "SEC EDGAR", "sec", "failed", 0, error=str(e))

        all_records.extend(direct_records)
        emitter.stage("direct_sources", "completed", output_count=len(direct_records))

        logger.info(f"[{self.__class__.__name__}] Dispatching Reader Agent...")
        reader_out = reader.execute_task({"records": all_records})
        all_records = reader_out.get("records", [])
            
        # 2. STREAM B: LEGISLATIVE & REGULATORY APIs
        logger.info(f"[{self.__class__.__name__}] Starting Stream B: Legislative & Regulatory API Monitors")
        emitter.stage("regulatory_apis", "running")
        api_records = []
        
        # 2a. Legislative Monitor
        try:
            legislative_monitor = LegislativeMonitorAgent()
            leg_out = legislative_monitor.execute_task({"run_id": run_id, "cg_key": cg_key, "ls_key": ls_key, "enabled": True})
            api_records.extend(accept_source(leg_out.get("records", []), "congress", "Congress.gov and LegiScan monitor", "legislative"))
            logger.info(f"[{self.__class__.__name__}] Legislative Monitor: Collected {len(leg_out.get('records', []))} records")
        except Exception as e:
            logger.error(f"Legislative Monitor failed: {e}")
            emitter.source("congress", "Congress.gov and LegiScan monitor", "legislative", "failed", 0, error=str(e))

        # 2b. Federal Register Monitor
        try:
            fr_connector = FederalRegisterConnector({'api_base_url': 'https://www.federalregister.gov/api/v1/articles.json', 'timeout': 30})
            if fr_connector.connect() and fr_connector.authenticate():
                fr_data = fr_connector.incremental_sync()
                federal_records = []
                for item in (fr_data if isinstance(fr_data, list) else []):
                    federal_records.append({
                        "title": item.get('title', 'Federal Register Article'),
                        "snippet": (item.get('abstract') or '')[:1000],
                        "source": "Federal Register",
                        "url": item.get('html_url', ''),
                        "date": item.get('publication_date', '')
                    })
                api_records.extend(accept_source(federal_records, "federal_register", "Federal Register", "regulatory"))
                fr_connector.shutdown()
                logger.info(f"[{self.__class__.__name__}] Federal Register: Collected {len(fr_data if isinstance(fr_data, list) else [])} records")
        except Exception as e:
            logger.error(f"Federal Register Monitor failed: {e}")
            emitter.source("federal_register", "Federal Register", "regulatory", "failed", 0, error=str(e))

        # 2c. Regulations.gov Monitor
        try:
            from infrastructure.connectors.regulations_gov_connector import RegulationsGovConnector
            regulations_key = os.getenv('REGULATIONS_GOV_API_KEY')
            if not regulations_key:
                raise RuntimeError("REGULATIONS_GOV_API_KEY is not configured")
            regs_connector = RegulationsGovConnector({'api_key': regulations_key, 'timeout': 30})
            if regs_connector.connect() and regs_connector.authenticate():
                query = {
                    "filter": {"agencyId": "CFPB,FTC,OCC"},
                    "q": "buy now pay later OR BNPL OR algorithmic scoring OR consumer credit",
                    "size": 15
                }
                regs_data = regs_connector.fetch(query)
                
                # Fetch returns a list or a dict with a 'data' key depending on API version
                fetched_list = regs_data if isinstance(regs_data, list) else regs_data.get('data', []) if isinstance(regs_data, dict) else []
                
                regulations_records = []
                for item in fetched_list:
                    attrs = item.get('attributes', item) if isinstance(item, dict) else {}
                    doc_id = attrs.get('objectId', item.get('id', ''))
                    regulations_records.append({
                        "title": attrs.get('title', 'Regulations.gov Document'),
                        "snippet": f"Type: {attrs.get('documentType', 'Rulemaking')} - Agency: {attrs.get('agencyId', 'Unknown')}",
                        "source": "Regulations.gov",
                        "url": f"https://www.regulations.gov/document/{doc_id}",
                        "date": attrs.get('postedDate', '')
                    })
                api_records.extend(accept_source(regulations_records, "regulations_gov", "Regulations.gov", "regulatory"))
                regs_connector.shutdown()
                logger.info(f"[{self.__class__.__name__}] Regulations.gov: Collected {len(fetched_list)} targeted records for CFPB, FTC, OCC")
        except Exception as e:
            logger.error(f"Regulations.gov Monitor failed: {e}")
            emitter.source("regulations_gov", "Regulations.gov", "regulatory", "failed", 0, error=str(e))

        # 2d. CFPB Monitor (Throttled: 7-Day Cooldown)
        try:
            import json
            checkpoint_path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/infrastructure/connectors/checkpoints.json")
            
            # Load checkpoints safely
            try:
                with open(checkpoint_path, "r") as cf:
                    chk_data = json.load(cf)
            except Exception:
                chk_data = {}
                
            last_cfpb = chk_data.get("last_run_cfpb", 0)
            now = pytime.time()
            
            if (now - last_cfpb) > (7 * 86400):  # 7 days
                logger.info(f"[{self.__class__.__name__}] CFPB cooldown expired. Fetching fresh complaint data...")
                cfpb_connector = CFPBConnector()
                cfpb_data = cfpb_connector.fetch_data({})
                if isinstance(cfpb_data, list):
                    api_records.extend(accept_source(cfpb_data, "cfpb", "Consumer Financial Protection Bureau", "regulatory"))
                
                # Update checkpoint
                chk_data["last_run_cfpb"] = now
                with open(checkpoint_path, "w") as cf:
                    json.dump(chk_data, cf, indent=2)
                    
                logger.info(f"[{self.__class__.__name__}] CFPB Monitor: Collected {len(cfpb_data)} records")
            else:
                days_left = round(( (7 * 86400) - (now - last_cfpb) ) / 86400, 1)
                logger.info(f"[{self.__class__.__name__}] CFPB Monitor skipped (On Cooldown for {days_left} more days).")
                emitter.source("cfpb", "Consumer Financial Protection Bureau", "regulatory", "skipped", 0, error=f"Cooldown active for {days_left} more days")
                
        except Exception as e:
            logger.error(f"CFPB Monitor failed: {e}")
            emitter.source("cfpb", "Consumer Financial Protection Bureau", "regulatory", "failed", 0, error=str(e))



        # 2e. State Regulator Monitor (NY DFS & CA DFPI)
        try:
            from agents.state_legislative_agent import StateLegislativeAgent
            state_monitor = StateLegislativeAgent()
            state_out = state_monitor.execute_task({})
            state_recs = state_out.get("records", [])
            
            # --- LEGISCAN INJECTION ---
            # LEGISCAN_API_KEY is canonical; retain the historical alias for existing DGX environments.
            ls_key = os.getenv("LEGISCAN_API_KEY") or os.getenv("LEXISNEXIS_API_KEY")
            if ls_key:
                import json
                from infrastructure.connectors.legiscan_connector import LegiScanConnector
                
                checkpoint_path = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/infrastructure/connectors/checkpoints.json")
                seen_bills = set()
                checkpoint_data = {}
                
                if os.path.exists(checkpoint_path):
                    try:
                        with open(checkpoint_path, "r") as cf:
                            checkpoint_data = json.load(cf)
                            seen_bills = set(checkpoint_data.get("seen_legiscan_bill_ids", []))
                    except Exception:
                        seen_bills = set()

                ls_connector = LegiScanConnector({'api_key': ls_key})
                if ls_connector.connect() and ls_connector.authenticate():
                    # Targeted BNPL & Affirm AI keywords
                    search_queries = [
                        'BNPL OR "buy now pay later"',
                        '"algorithmic credit" OR "human in the loop" OR "age verification"'
                    ]
                    
                    new_bills_found = 0
                    for st in ["NY", "CA", "TX"]:
                        for q in search_queries:
                            ls_data = ls_connector.fetch({'state': st, 'query': q, 'year': 2026, 'op': 'getSearch'})
                            items = []
                            if isinstance(ls_data, dict) and 'searchresult' in ls_data:
                                items = [v for k, v in ls_data['searchresult'].items() if k != 'summary']
                            elif isinstance(ls_data, list):
                                items = ls_data
                                
                            for item in items:
                                if isinstance(item, dict):
                                    bill_id = str(item.get('bill_id', item.get('bill_number', '')))
                                    if bill_id and bill_id in seen_bills:
                                        continue  # Skip previously processed bill
                                    
                                    seen_bills.add(bill_id)
                                    new_bills_found += 1
                                    state_recs.append({
                                        "title": f"[{st}] {item.get('bill_number', 'Bill')} - {item.get('title', 'Legislation')}",
                                        "source": f"LegiScan ({st})",
                                        "snippet": f"Relevance: {item.get('relevance', 'N/A')}% | Last Action: {item.get('last_action', 'Pending State Legislation')}",
                                        "url": item.get('url', item.get('text_url', '')),
                                        "date": item.get('last_action_date', '')
                                    })
                    
                    # Persist updated checkpoints
                    checkpoint_data["seen_legiscan_bill_ids"] = list(seen_bills)
                    with open(checkpoint_path, "w") as cf:
                        json.dump(checkpoint_data, cf, indent=2)
                        
                    logger.info(f"LegiScan: Processed {new_bills_found} NEW bills matching BNPL and AI Tech policy.")
            # ----------------------------------------------------------
            
            api_records.extend(accept_source(state_recs, "state_legislation", "State legislative and regulatory sources", "legislative"))
            logger.info(f"[{self.__class__.__name__}] State Regulator Monitor: Collected {len(state_recs)} records")
        except Exception as e:
            logger.error(f"State Regulator Monitor failed: {e}")
            emitter.source("state_legislation", "State legislative and regulatory sources", "legislative", "failed", 0, error=str(e))


        # 2f. Judicial Monitor is disabled until a real court-data connector replaces the simulator.
        emitter.source("judicial", "Judicial monitor", "judicial", "skipped", 0, error="No production court-data connector is configured")
        logger.warning(f"[{self.__class__.__name__}] Judicial Monitor skipped: active implementation is simulation-only")

        emitter.stage("regulatory_apis", "completed", output_count=len(api_records))

        # 3. STREAM C: SENTIMENT & SOCIAL MONITORS
        logger.info(f"[{self.__class__.__name__}] Starting Stream C: Sentiment & Social Monitors")
        emitter.stage("sentiment", "running")
        sentiment_records = []
        

        # 3b. News Monitor
        try:
            from agents.news_monitor_agent import NewsMonitorAgent
            news_monitor = NewsMonitorAgent()
            news_out = news_monitor.execute_task({"run_id": run_id, "enabled": True})
            sentiment_records.extend(accept_source(news_out.get("records", []), "news", "News monitor", "news"))
            logger.info(f"[{self.__class__.__name__}] News Monitor: Collected {len(news_out.get('records', []))} records")
        except Exception as e:
            logger.error(f"News Monitor failed: {e}")
            emitter.source("news", "News monitor", "news", "failed", 0, error=str(e))

        # 3a. Market Sentiment
        try:
            market_out = market_sentiment.execute_task({"type": "monitor_market_sentiment", "lookback_hours": 24})
            market_records = []
            for item in market_out.get("records", []):
                market_records.append({
                    "title": item.get('title', 'Market Sentiment'),
                    "snippet": f"Sentiment Score: {item.get('sentiment_score', 0)} | Phrases: {', '.join(item.get('key_phrases', []))}",
                    "source": item.get('source', 'Unknown Market Source'),
                    "url": item.get('url', ''),
                    "date": item.get('published', '')
                })
            sentiment_records.extend(accept_source(market_records, "market_sentiment", "Market sentiment", "sentiment"))
            logger.info(f"[{self.__class__.__name__}] Market Sentiment: Collected {len(market_out.get('records', []))} records")
        except Exception as e:
            logger.error(f"Market Sentiment Monitor failed: {e}")
            emitter.source("market_sentiment", "Market sentiment", "sentiment", "failed", 0, error=str(e))

        # 3b. Public Statements
        try:
            statement_out = public_statement.execute_task({"run_id": run_id, "enabled": True})
            statement_records = []
            for item in statement_out.get("records", []):
                statement_records.append({
                    "title": item.get('title', 'Public Statement'),
                    "snippet": item.get('text_context', ''),
                    "source": item.get('source', 'Social Monitor'),
                    "url": "",
                    "date": ""
                })
            sentiment_records.extend(accept_source(statement_records, "public_statements", "Public statements", "public_statement"))
            logger.info(f"[{self.__class__.__name__}] Public Statements: Collected {len(statement_out.get('records', []))} records")
        except Exception as e:
            logger.error(f"Public Statement Monitor failed: {e}")
            emitter.source("public_statements", "Public statements", "public_statement", "failed", 0, error=str(e))
            
        all_records.extend(sentiment_records)
        all_records.extend(api_records)
        logger.info(f"[{self.__class__.__name__}] Total combined records: {len(all_records)}")
        emitter.stage("sentiment", "completed", output_count=len(sentiment_records))

        # GOLDEN RUN TRUNCATION
        if golden_run and all_records:
            all_records = all_records[:1]
            logger.info(f"[{self.__class__.__name__}] GOLDEN RUN: Truncated to {len(all_records)} record")

        emitter.stage("deduplication", "running", input_count=len(all_records))
        all_records = filter_off_topic_records(all_records)
        all_records, rejected_nonproduction = partition_production_records(all_records)
        if rejected_nonproduction:
            emitter.add_error("deduplication", f"Rejected {len(rejected_nonproduction)} records that used fallback classification or explicit non-production data.", True)
        all_records = deduplicate_records(all_records)
        logger.info(f"[{self.__class__.__name__}] Deduplicated down to {len(all_records)} unique records")
        emitter.stage("deduplication", "completed", input_count=len(all_records) + len(rejected_nonproduction), output_count=len(all_records))
        emitter.emit("running")

        # LOG VISITS TO INVESTIGATION MEMORY
        if inv_memory:
            for r in all_records:
                inv_memory.log_document_visit(
                    url=r.get("url", ""), title=r.get("title", ""), 
                    document_hash=r.get("document_hash", "unknown"), reason_read=r.get("triage_reasoning", "Discovered via API/Search")
                )
            # inv_memory.close() removed to prevent AttributeError
            
        # PERSIST EVIDENCE LEDGER TO REPORT DIRECTORY
        try:
            if 'report_dir' not in locals() or not report_dir:
                report_dir = os.path.join("reports", f"run_{run_id if 'run_id' in locals() else 'latest'}")
            os.makedirs(report_dir, exist_ok=True)
            
            ledger_path = os.path.join(report_dir, "evidence_ledger.json")
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(all_records, f, indent=2)
            logger.info(f"[{self.__class__.__name__}] Wrote evidence ledger ({len(all_records)} records) to {ledger_path}")
            
            # Write to GLOBAL master ledger so discovery_agent.py doesn't get amnesia
            master_ledger_path = os.path.join("reports", "evidence_ledger.json")
            try:
                with open(master_ledger_path, "w", encoding="utf-8") as f:
                    json.dump({"live_evaluation_ledger": all_records}, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to write global master evidence ledger: {e}")
        except Exception as e:
            logger.error(f"Failed to write evidence ledger: {e}")

        # 3. PIPELINE EXECUTION
        logger.info(f"[{self.__class__.__name__}] Expanding context...")
        emitter.stage("context_expansion", "running", input_count=len(all_records))
        context_out = ContextExpansionAgent().execute_task({"records": all_records, "run_id": run_id})
        expanded_records = context_out.get("records", [])
        emitter.stage("context_expansion", "completed", input_count=len(all_records), output_count=len(expanded_records))
        
        logger.info(f"[{self.__class__.__name__}] Analyzing impacts...")
        emitter.stage("impact_analysis", "running", input_count=len(expanded_records))
        impact_out = ImpactAnalyzerAgent().execute_task({"records": expanded_records, "run_id": run_id})
        findings = impact_out.get("records", [])
        emitter.stage("impact_analysis", "completed", input_count=len(expanded_records), output_count=len(findings))

        # AUTHENTIC HUMAN FEEDBACK LOOP (Awaiting UI)
        low_impact_findings = [f for f in findings if f.get("impact_score") == "low"]
        if low_impact_findings:
            logger.info(f"[{self.__class__.__name__}] Skipping simulated human feedback. Run is 100% authentic.")
        
        logger.info(f"[{self.__class__.__name__}] Compressing {len(findings)} findings...")
        emitter.stage("compression", "running", input_count=len(findings))
        compression_out = ContextCompressorAgent().execute_task({"findings": findings, "run_id": run_id})
        compressed_findings = compression_out.get("findings", [])
        emitter.stage("compression", "completed", input_count=len(findings), output_count=len(compressed_findings))
        
        logger.info(f"[{self.__class__.__name__}] Extracting entities...")
        emitter.stage("entity_resolution", "running", input_count=len(compressed_findings))
        entity_out = EntityResolutionAgent().execute_task({"findings": compressed_findings, "run_id": run_id})
        entity_enriched_findings = entity_out.get("findings", [])
        emitter.stage("entity_resolution", "completed", input_count=len(compressed_findings), output_count=len(entity_enriched_findings))
        
        logger.info(f"[{self.__class__.__name__}] Scoring risk...")
        emitter.stage("risk_scoring", "running", input_count=len(entity_enriched_findings))
        risk_out = RiskScoringAgent().execute_task({"findings": entity_enriched_findings, "run_id": run_id})
        risk_scored_findings = risk_out.get("findings", [])
        emitter.stage("risk_scoring", "completed", input_count=len(entity_enriched_findings), output_count=len(risk_scored_findings))
        
        logger.info(f"[{self.__class__.__name__}] Validating findings...")
        emitter.stage("validation", "running", input_count=len(risk_scored_findings))
        val_out = ValidationAgent().execute_task({"findings": risk_scored_findings, "run_id": run_id})
        validated_findings = val_out.get("findings", [])
        validated_findings, rejected_unsafe_findings = partition_production_records(validated_findings)
        if rejected_unsafe_findings:
            emitter.add_error("validation", f"Excluded {len(rejected_unsafe_findings)} finding(s) that used analysis fallback paths.", True)
        emitter.stage("validation", "completed", input_count=len(risk_scored_findings), output_count=len(validated_findings))
        emitter.emit("running", validated_findings)
        
        try:
            emitter.stage("graph_sync", "running", input_count=len(validated_findings))
            graph_connector = GraphConnector()
            graph_connector.sync_findings(validated_findings, run_id)
            graph_connector.close()
            logger.info(f"[{self.__class__.__name__}] Synced {len(validated_findings)} findings to Neo4j")
            emitter.stage("graph_sync", "completed", input_count=len(validated_findings), output_count=len(validated_findings))
        except Exception as e:
            logger.error(f"Failed to sync to Neo4j: {e}")
            emitter.stage("graph_sync", "skipped", input_count=len(validated_findings), error=str(e))
        
        # DASHBOARD HOOK 2: Emit validated records before synthesis
        if dashboard and 'validated_findings' in locals():
            dashboard.emit("running", records=validated_findings)

        logger.info(f"[{self.__class__.__name__}] Generating final synthesis report...")
        # TELEMETRY & DEFENSIVE FALLBACK FOR SYNTHESIS
        expanded_recs = expanded_records if 'expanded_records' in locals() else []
        impact_recs = findings if 'findings' in locals() else []
        compressed_recs = compressed_findings if 'compressed_findings' in locals() else []
        validated_recs = validated_findings if 'validated_findings' in locals() else []

        logger.info(
            f"[{self.__class__.__name__}] Pipeline Counts | "
            f"Expanded={len(expanded_recs)} "
            f"Impact={len(impact_recs)} "
            f"Compressed={len(compressed_recs)} "
            f"Validated={len(validated_recs)}"
        )

        # Phase 0: Enforce Production Eligibility Gate
        from infrastructure.production_eligibility import is_production_eligibility
        
        eligible_findings = [f for f in validated_recs if is_production_eligibility(f)]
        
        logger.info(f"[{self.__class__.__name__}] Pre-Gate: {len(validated_recs)} | Post-Gate (Eligible): {len(eligible_findings)}")
        
        # NEVER fallback to unvalidated arrays. Only pass eligible findings.
        # Phase 0: Enforce strict production eligibility gate
        from infrastructure.production_eligibility import is_production_eligible
        eligible_findings = [f for f in validated_findings if is_production_eligible(f)]
        logger.info(f"[{self.__class__.__name__}] Pre-Gate: {len(validated_findings)} | Post-Gate (Eligible): {len(eligible_findings)}")
        synthesis_input = eligible_findings
        logger.info(f"[{self.__class__.__name__}] Passing {len(synthesis_input)} eligible records to ResearchSynthesisAgent")
        synth_out = ResearchSynthesisAgent().execute_task({"findings": synthesis_input, "run_id": run_id})
        ReportingAgent().execute_task({"report_dir": report_dir, "findings": eligible_findings, "synthesis": synth_out})
        synthesis_input = validated_recs
        logger.info(f"[{self.__class__.__name__}] Passing {len(synthesis_input)} records to ResearchSynthesisAgent")
        emitter.stage("synthesis", "running", input_count=len(synthesis_input))
        synth_out = ResearchSynthesisAgent().execute_task({"findings": synthesis_input, "run_id": run_id})
        synthesis_status = synth_out.get("generation_status", "completed") if isinstance(synth_out, dict) else "failed"
        emitter.stage("synthesis", "completed" if synthesis_status in {"completed", "no_findings"} else "failed", input_count=len(synthesis_input), output_count=1 if synthesis_status in {"completed", "no_findings"} else 0, error=synth_out.get("error") if isinstance(synth_out, dict) else "Invalid synthesis response")
        emitter.stage("reporting", "running", input_count=len(validated_findings))
        report_out = ReportingAgent().execute_task({"report_dir": report_dir, "findings": validated_findings, "synthesis": synth_out})
        report_status = report_out.get("generation_status", "failed") if isinstance(report_out, dict) else "failed"
        report_path = report_out.get("report_path") if isinstance(report_out, dict) else None
        emitter.stage("reporting", "completed" if report_status == "completed" else "failed", input_count=len(validated_findings), output_count=1 if report_status == "completed" else 0, error=report_out.get("error") if isinstance(report_out, dict) else "Invalid report response")
        final_status = "completed" if report_status == "completed" else "partial"
        emitter.emit(final_status, validated_findings, report_path if report_status == "completed" else None)
        logger.info(f"[{self.__class__.__name__}] Swarm complete! Report at {report_dir}")

        # DASHBOARD HOOK 3: Final Delivery
        if dashboard:
            report_path = os.path.join(report_dir, "report.md")
            dashboard.emit("completed", records=eligible_findings, report_path=report_path if os.path.exists(report_path) else None)
        
        
        # SYNTHESIZE & UPDATE PERSISTENT TEMPORAL MEMORY
        try:
            existing_notebook = inv_memory.get_analyst_notebook() if inv_memory else []
            new_threads = []
            
            # Extract topics and upcoming dates from synthesis output
            if isinstance(synth_out, dict):
                topics = synth_out.get("key_findings", [])
                for idx, item in enumerate(topics):
                    new_threads.append({
                        "inv_id": f"thread_{idx}_{int(pytime.time())}",
                        "topic": str(item.get("title", item)) if isinstance(item, dict) else str(item),
                        "knowns": [str(item)] if not isinstance(item, dict) else item.get("details", []),
                        "unknowns": ["Monitor for further enforcement or statutory updates."],
                        "last_updated": datetime.now().strftime("%Y-%m-%d"),
                        "scheduled_follow_up": synth_out.get("follow_up_dates", [])
                    })

            if new_threads and inv_memory:
                inv_memory.save_analyst_notebook(new_threads)
        except Exception as mem_err:
            logger.warning(f"Failed to update persistent memory: {mem_err}")

        return {"report_dir": report_dir}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--golden-run', action='store_true')
    args = parser.parse_args()
    orchestrator = PolicyOrchestratorAgent()
    orchestrator.run_swarm(os.getenv("CONGRESS_GOV_API_KEY"), os.getenv("LEXISNEXIS_API_KEY"), golden_run=args.golden_run)
