import os, re

base = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/agents")

SEARCH_HELPER = '''
    def _perform_live_search_fallback(self, query: str, max_results: int = 3):
        """Tier 2 Fallback: Search web when primary feeds fail or return empty."""
        print(f"[{self.agent_id}]  Tier 2: Searching web for '{query}'...")
        fallback_records = []
        try:
            import urllib.parse, urllib.request
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            
            titles = re.findall(r'<a class="result__a"[^>]*>(.*?)</a>', html)
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html)
            
            for i in range(min(len(titles), max_results)):
                clean_title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else clean_title
                fallback_records.append({
                    "title": clean_title,
                    "description": clean_snippet,
                    "link": f"search_fallback_{i}"
                })
            print(f"[{self.agent_id}]  Tier 2 Recovered {len(fallback_records)} organic search items.")
        except Exception as e:
            print(f"[{self.agent_id}]  Tier 2 Search failed ({e}). Escalating to Tier 3.")
        return fallback_records
'''

def inject_helper(file_path):
    with open(file_path, "r") as f:
        code = f.read()
    if "_perform_live_search_fallback" not in code:
        code = re.sub(r"(class \w+:)", r"\1\n" + SEARCH_HELPER, code, count=1)
        with open(file_path, "w") as f:
            f.write(code)

# 1. Patch news_monitor_agent.py
news_path = os.path.join(base, "news_monitor_agent.py")
if os.path.exists(news_path):
    inject_helper(news_path)
    with open(news_path, "r") as f:
        code = f.read()
    
    pat = r"# If we found items, use the first one; otherwise, use mock.*?records\.append\(record\).*?except Exception as e:.*?records\.append\(record\)"
    repl = '''if not items:
                    print(f"[{self.agent_id}] Tier 1 empty for {source_name}. Escalating to Tier 2...")
                    items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} Buy Now Pay Later regulation")

                if items:
                    for item in items[:3]:
                        record = {
                            "source": source_name.replace('_', ' ').title(),
                            "jurisdiction": "US",
                            "title": item.get("title", "Financial News Update"),
                            "text_context": item.get("description", ""),
                        }
                        records.append(record)
                    registry.update_source_health(source_name, success=True)
                else:
                    print(f"[{self.agent_id}] Tier 3 Triggered: 0 records found for {source_name}.")
                    registry.update_source_health(source_name, success=False, error="Tier 1 & 2 yield 0 records")

            except Exception as e:
                print(f"[{self.agent_id}] Tier 1 Fetch Error for {source_name}: {e}. Escalating to Tier 2...")
                fallback_items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} Buy Now Pay Later regulation")
                if fallback_items:
                    for item in fallback_items[:3]:
                        records.append({
                            "source": source_name.replace('_', ' ').title(),
                            "jurisdiction": "US",
                            "title": item.get("title", "Financial News Update"),
                            "text_context": item.get("description", ""),
                        })
                    registry.update_source_health(source_name, success=True)
                else:
                    registry.update_source_health(source_name, success=False, error=str(e))
                continue'''
    
    new_code, count = re.subn(pat, repl, code, flags=re.DOTALL)
    if count > 0:
        with open(news_path, "w") as f:
            f.write(new_code)
        print("✅ Patched news_monitor_agent.py")

# 2. Patch policymaker_monitor_agent.py
policy_path = os.path.join(base, "policymaker_monitor_agent.py")
if os.path.exists(policy_path):
    inject_helper(policy_path)
    with open(policy_path, "r") as f:
        code = f.read()
    
    pat = r"# If we found items, use the first one; otherwise, use mock.*?records\.append\(record\).*?except Exception as e:.*?records\.append\(record\)"
    repl = '''if not items:
                            print(f"[{self.agent_id}] Tier 1 empty for {source_name}. Escalating to Tier 2...")
                            items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} Senate Banking CFPB statement")

                        if items:
                            for item in items[:3]:
                                record = {
                                    "source": source_name.replace('_', ' ').title(),
                                    "jurisdiction": "US Federal",
                                    "title": item.get("title", "Statement on Financial Policy"),
                                    "text_context": f"{item.get('title', '')}. {item.get('description', '')}",
                                }
                                records.append(record)
                            registry.update_source_health(source_name, success=True)
                        else:
                            print(f"[{self.agent_id}] Tier 3 Triggered: 0 records found for {source_name}.")
                            registry.update_source_health(source_name, success=False, error="Tier 1 & 2 yield 0 records")

            except Exception as e:
                print(f"[{self.agent_id}] Tier 1 Fetch Error for {source_name}: {e}. Escalating to Tier 2...")
                fallback_items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} Senate Banking CFPB statement")
                if fallback_items:
                    for item in fallback_items[:3]:
                        records.append({
                            "source": source_name.replace('_', ' ').title(),
                            "jurisdiction": "US Federal",
                            "title": item.get("title", "Statement on Financial Policy"),
                            "text_context": f"{item.get('title', '')}. {item.get('description', '')}",
                        })
                    registry.update_source_health(source_name, success=True)
                else:
                    registry.update_source_health(source_name, success=False, error=str(e))
                continue'''
    
    new_code, count = re.subn(pat, repl, code, flags=re.DOTALL)
    if count > 0:
        with open(policy_path, "w") as f:
            f.write(new_code)
        print("✅ Patched policymaker_monitor_agent.py")

# 3. Patch public_statement_monitor_agent.py
pub_path = os.path.join(base, "public_statement_monitor_agent.py")
if os.path.exists(pub_path):
    inject_helper(pub_path)
    with open(pub_path, "r") as f:
        code = f.read()
    
    pat = r"# Live integration logic goes here.*?pass"
    repl = '''search_items = self._perform_live_search_fallback(f"{source_name.replace('_', ' ')} CFPB Twitter public statement Buy Now Pay Later")
            if search_items:
                for item in search_items[:3]:
                    records.append({
                        "source": source_name.replace('_', ' ').title(),
                        "jurisdiction": "US Federal",
                        "title": item.get("title", "Public Statement"),
                        "text_context": item.get("description", ""),
                        "url": "https://www.consumerfinance.gov/"
                    })'''
    
    new_code, count = re.subn(pat, repl, code, flags=re.DOTALL)
    if count > 0:
        with open(pub_path, "w") as f:
            f.write(new_code)
        print("✅ Patched public_statement_monitor_agent.py")

# 4. Patch regulatory_watch.py
reg_path = os.path.join(base, "regulatory_watch.py")
if os.path.exists(reg_path):
    inject_helper(reg_path)
    with open(reg_path, "r") as f:
        code = f.read()
    
    pat = r"# For simulation, return mock data based on jurisdiction and agencies.*?return relevant_items"
    repl = '''self.log_thought(f"Executing Tier 1 & Tier 2 search for {jurisdiction} / {product}...")
        search_results = self._perform_live_search_fallback(f"{jurisdiction} {product} regulatory guidance CFPB FTC DFPI 2026", max_results=5)
        if not search_results:
            self.log_thought(f"Tier 3 Triggered: Returning 0 records for {jurisdiction} / {product}.")
            return []
            
        return [{
            "agency": jurisdiction,
            "type": "guidance",
            "title": item["title"],
            "reference": "Web Search Discovery",
            "text_context": item["description"],
            "url": item.get("link", ""),
            "relevance_score": 0.85
        } for item in search_results]'''
    
    new_code, count = re.subn(pat, repl, code, flags=re.DOTALL)
    if count > 0:
        with open(reg_path, "w") as f:
            f.write(new_code)
        print("✅ Patched regulatory_watch.py")

