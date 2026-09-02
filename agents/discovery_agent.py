import logging
import json
import re
import subprocess
import urllib.parse
import glob
import os
from datetime import datetime
import concurrent.futures
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

class DiscoveryAgent:

    def __init__(self, agent_id="discovery_agent", model="qwen"):
        self.agent_id = agent_id
        self.model = model
        self.institutional_seeds = [
            {"title": "CFPB Buy Now Pay Later Interpretive Rule & Guidance", "snippet": "CFPB guidance regarding digital installment loans and truth in lending regulations for BNPL providers.", "url": "https://www.consumerfinance.gov/about-us/newsroom/cfpb-issues-guidance-to-treat-buy-now-pay-later-lenders-like-traditional-credit-card-companies/"},
            {"title": "Federal Register: Truth in Lending (Regulation Z) BNPL Updates", "snippet": "Federal regulatory updates concerning open-end credit and point-of-sale financing disclosures.", "url": "https://www.federalregister.gov/documents/current"},
            {"title": "California DFPI Fintech Law Compliance", "snippet": "California Department of Financial Protection oversight on installment lenders.", "url": "https://dfpi.ca.gov/fintech/"}
        ]

    def gatekeeper_check(self, query, text_snippet, threshold=6):
        prompt = (
            f"Analyze this snippet regarding '{query}'. Score 1-10 on regulatory risk/momentum."
            " Reply ONLY with the integer score inside XML tags, like <SCORE>7</SCORE>."
            f" Snippet: {text_snippet[:1000]}"
        )
        try:
            res = subprocess.run(["ollama", "run", self.model], input=prompt.encode("utf-8"), capture_output=True)
            match = re.search(r"<SCORE>\s*([0-9]+)\s*</SCORE>", res.stdout.decode("utf-8"), re.IGNORECASE)
            return min(10, int(match.group(1))) >= threshold if match else False
        except Exception:
            return False

    def _sanitize_query(self, query: str) -> str:
        q = str(query)
        q = re.sub(r'since:\S+', '', q, flags=re.IGNORECASE)
        q = re.sub(r'AFTER:\S+', '', q, flags=re.IGNORECASE)
        q = re.sub(r'BEFORE:\S+', '', q, flags=re.IGNORECASE)
        q = re.sub(r'intitle:', '', q, flags=re.IGNORECASE)
        q = re.sub(r'inurl:', '', q, flags=re.IGNORECASE)
        q = re.sub(r'\b(AND|OR|NOT)\b', ' ', q)
        q = re.sub(r'[\(\)]', ' ', q)
        q = re.sub(r'\s+', ' ', q).strip()
        return q

    def _search_worker(self, query, attempt_num=1):
        hits = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                page = context.new_page()
                stealth_sync(page)

                clean_q = self._sanitize_query(query)
                
                # 1. Try Google First (The Human OSINT Standard)
                google_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(clean_q)}"
                try:
                    page.goto(google_url, timeout=15000, wait_until="domcontentloaded")
                    page.wait_for_selector("div.g", timeout=5000)
                    page.wait_for_timeout(1000)
                    raw_els = page.query_selector_all("div.g")
                    for el in raw_els[:10]:
                        t_el = el.query_selector("h3")
                        a_el = el.query_selector("a")
                        s_el = el.query_selector("div[data-sncf], .VwiC3b")
                        if t_el and a_el:
                            href = a_el.get_attribute("href")
                            if href and href.startswith("http"):
                                hits.append({
                                    "query_vector": query,
                                    "title": t_el.inner_text().strip(),
                                    "snippet": s_el.inner_text().strip() if s_el else "",
                                    "url": href
                                })
                except Exception:
                    pass

                # 2. Fallback to Bing if Google yielded 0 hits (Captcha/Block)
                if not hits:
                    bing_url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(clean_q)}"
                    try:
                        page.goto(bing_url, timeout=15000, wait_until="domcontentloaded")
                        page.wait_for_selector(".b_algo", timeout=5000)
                        page.wait_for_timeout(1000)
                        raw_els = page.query_selector_all(".b_algo")
                        for el in raw_els[:10]:
                            t_el = el.query_selector("h2 a")
                            s_el = el.query_selector(".b_caption p")
                            if t_el:
                                href = t_el.get_attribute("href")
                                if href and href.startswith("http"):
                                    if "u=a1" in href:
                                        import base64
                                        try:
                                            b64_str = href.split("u=a1")[1].split("&")[0]
                                            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
                                            href = base64.urlsafe_b64decode(b64_str).decode("utf-8", errors="ignore")
                                        except: pass
                                    hits.append({
                                        "query_vector": query,
                                        "title": t_el.inner_text().strip(),
                                        "snippet": s_el.inner_text().strip() if s_el else t_el.inner_text().strip(),
                                        "url": href
                                    })
                    except Exception:
                        pass

                # 3. The "Human Researcher" Direct Navigation Fallback
                if not hits and "site:" in clean_q:
                    import re as reg_mod
                    site_match = reg_mod.search(r'site:([^\s]+)', clean_q)
                    if site_match:
                        domain = site_match.group(1)
                        hits.append({
                            "query_vector": query,
                            "title": f"Direct Navigation: {domain}",
                            "snippet": "Search engines blocked. Performing direct site reconnaissance.",
                            "url": f"https://{domain}"
                        })

                # Apply blocklist filter
                filtered_hits = []
                blocklist = [
                    "etsy.com", "costco.com", "bestbuy.com", "amazon.com", "walmart.com",
                    "target.com", "ebay.com", "bedbathandbeyond.com", "buybuybaby.com",
                    "merriam-webster", "dictionary.com", "poynter.org", "wikipedia.org",
                    "experian.com", "creditkarma.com", "transunion.com", "equifax.com",
                    "grammarist.com", "vocabulary.com", "thefreedictionary.com", "interpretive.com"
                ]
                for h in hits:
                    check_text = f"{h['url']} {h['title']} {h['snippet']}".lower()
                    if not any(noise in check_text for noise in blocklist):
                        filtered_hits.append(h)

                browser.close()
                return filtered_hits

        except Exception as e:
            logging.error(f"[{self.agent_id}] Playwright Hunter thread error: {e}")
        
        return hits

    
    def _deep_scrape_worker(self, url):
        full_text = ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US"
                )
                page = context.new_page()
                stealth_sync(page)
                try:
                    page.goto(url, timeout=20000, wait_until="domcontentloaded")
                    page.wait_for_timeout(1000)
                    
                    try:
                        full_text = page.evaluate("document.body.innerText")
                    except Exception as eval_err:
                        if "Execution context was destroyed" in str(eval_err):
                            # If a redirect happened mid-read, wait for the new page and try again
                            page.wait_for_load_state("domcontentloaded", timeout=5000)
                            full_text = page.evaluate("document.body.innerText")
                            
                    if full_text: 
                        full_text = re.sub(r'\n{3,}', '\n\n', full_text).strip()
                except Exception as err:
                    logging.warning(f"[{self.agent_id}] Deep scrape timeout for {url}: {err}")
                browser.close()
        except Exception as e:
            logging.error(f"[{self.agent_id}] Deep Diver thread error: {e}")
        return full_text

    # PIPELINE ORCHESTRATION & RELENTLESS LOOP
    # ==========================================
    def execute_task(self, task_data):
        current_queries = task_data.get("queries", [])
        if not current_queries:
            current_queries = ["CFPB buy now pay later regulation", "State BNPL point of sale law"]
            
        records = []
        seen_urls = set()
        
        # --- DEEP HISTORICAL MEMORY ---
        import glob, json
        ledger_pattern = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/reports/live_runs/*/evidence_ledger.json")
        for ledger_path in glob.glob(ledger_pattern):
            try:
                with open(ledger_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        seen_urls.update(item.get("url") for item in data if item.get("url"))
                    elif isinstance(data, dict):
                        seen_urls.update(item.get("url") for item in data.get("live_evaluation_ledger", []) if item.get("url"))
            except Exception:
                pass

        logging.info(f"[{self.agent_id}] Loaded {len(seen_urls)} previously visited URLs. Commencing high-volume harvest.")
        logging.info(f"[{self.agent_id}] 🚀 EXECUTING MASSIVE PLAYWRIGHT SWEEP | Queries: {len(current_queries)}")
        
        all_hits = []
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_query = {executor.submit(self._search_worker, q, 1): q for q in current_queries}
            for future in concurrent.futures.as_completed(future_to_query):
                try:
                    all_hits.extend(future.result())
                except Exception:
                    pass

        candidates = []
        for r in all_hits:
            url = r["url"]
            if url in seen_urls: continue
            
            if self.gatekeeper_check(r["query_vector"], r["snippet"], threshold=6):
                r["source"] = "Web Intelligence"
                r["text_context"] = f"{r['title']} - {r['snippet']}"
                r["date"] = datetime.now().strftime('%Y-%m-%d')
                r["jurisdiction"] = "Multi-Jurisdictional"
                candidates.append(r)
                seen_urls.add(url)

        # MASSIVE DEEP SCRAPE BATCH
        if candidates:
            logging.info(f"[{self.agent_id}] 🤿 Routing {len(candidates)} high-signal targets to Playwright Deep Divers...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(self._deep_scrape_worker, c["url"]): c for c in candidates}
                for future in concurrent.futures.as_completed(futures):
                    try:
                        c = futures[future]
                        text = future.result()
                        c["full_text"] = text if text and len(text) > 150 else c["snippet"]
                        c["text_context"] = c["full_text"]
                        records.append(c)
                    except Exception:
                        pass

        logging.info(f"[{self.agent_id}] Playwright Discovery complete. Secured {len(records)} targets from {len(current_queries)} queries.")
        task_data["records"] = records
        return task_data