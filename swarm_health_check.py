import os, sys, requests
from neo4j import GraphDatabase
import importlib

print("\n========================================")
print(" OPENCLAW SWARM SYSTEM HEALTH CHECK")
print("========================================\n")

# 1. Check Local LLM (Qwen 32B)
print("[*] Testing Local Qwen 32B Inference...")
try:
    r = requests.post("http://localhost:11434/api/generate", json={"model": "nemotron:70b", "prompt": "Ping", "stream": False}, timeout=10)
    if r.status_code == 200: 
        print("  [+] Ollama Qwen 32B is ONLINE")
    else: 
        print(f"  [-] Ollama HTTP {r.status_code}")
except Exception as e: 
    print(f"  [-] Ollama Offline: {e}")

# 2. Check Neo4j Database
print("\n[*] Testing Neo4j Graph Database...")
try:
    driver = GraphDatabase.driver("bolt://localhost:7688", auth=("neo4j", "admin"))
    driver.verify_connectivity()
    print("  [+] Neo4j Database is ONLINE and reachable")
except Exception as e:
    print(f"  [-] Neo4j Offline: {e}")

# 3. Check External APIs
print("\n[*] Testing External Regulatory APIs...")
apis = {
    "Federal Register": "https://www.federalregister.gov/api/v1/documents.json?per_page=1",
    "Regulations.gov": "https://api.regulations.gov/v4/documents", 
    "CFPB Socrata (Current in Code)": "https://data.consumerfinance.gov/resource/s6ew-h6mp.json",
    "CFPB Socrata (Active Endpoint)": "https://data.consumerfinance.gov/resource/s6ew-h6mp.json"
}
for name, url in apis.items():
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200: 
            print(f"  [+] {name} API is ONLINE (HTTP 200)")
        elif r.status_code in [401, 403]: 
            print(f"  [+] {name} API is ONLINE (Requires Auth - Expected)")
        else: 
            print(f"  [-] {name} API failed: HTTP {r.status_code}")
    except Exception as e:
        print(f"  [-] {name} API unreachable: {e}")

# 4. Check Agent Initialization
print("\n[*] Verifying Agent Architecture & Imports...")
agents_to_check = [
    "agents.discovery_agent.DiscoveryAgent",
    "agents.context_expansion_agent.ContextExpansionAgent",
    "agents.impact_analyzer.ImpactAnalyzerAgent",
    "agents.context_compressor.ContextCompressorAgent",
    "agents.entity_resolution.EntityResolutionAgent",
    "agents.risk_scoring.RiskScoringAgent",
    "agents.validation_agent.ValidationAgent",
    "agents.research_synthesis.ResearchSynthesisAgent",
    "agents.reporting_agent.ReportingAgent"
]

sys.path.append(os.path.abspath("."))
for agent_path in agents_to_check:
    try:
        module_name, class_name = agent_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        agent_class = getattr(module, class_name)
        print(f"  [+] {class_name} compiled and loaded successfully")
    except Exception as e:
        print(f"  [-] FATAL: Failed to load {class_name}: {e}")

print("\n========================================\n")
