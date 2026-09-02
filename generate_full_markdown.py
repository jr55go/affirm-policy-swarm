import os, sys, json
import urllib.request
from neo4j import GraphDatabase

passwords = ["secret123", "admin", "password", "neo4j", "admin123"]
ports = ["7688", "7687"]
driver = None

print("🔍 Connecting to Neo4j...")
for port in ports:
    for pwd in passwords:
        try:
            d = GraphDatabase.driver(f"bolt://localhost:{port}", auth=("neo4j", pwd))
            d.verify_connectivity()
            driver = d
            break
        except: pass
    if driver: break

if not driver:
    print("❌ Could not connect to Neo4j.")
    sys.exit(1)

findings = []
with driver.session() as session:
    res = session.run("MATCH (n) WHERE n.run_id = 'run_1784849116' RETURN properties(n) as props")
    findings = [r["props"] for r in res]
    if not findings:
        res = session.run("MATCH (n) RETURN properties(n) as props LIMIT 120")
        findings = [r["props"] for r in res]

# Sort by risk score so the LLM focuses on the most critical data
try:
    findings.sort(key=lambda x: int(x.get('policy_risk_score', 0)), reverse=True)
except:
    pass

print(f"✅ Recovered {len(findings)} findings.")
print("🧠 Sending directly to Nemotron-70B for Markdown Synthesis (Takes 1-3 mins)...")

# Compile the top findings to avoid context window overflow
findings_text = ""
for i, f in enumerate(findings[:50]): 
    findings_text += f"Finding {i+1}:\nTitle: {f.get('title', 'N/A')}\nContext: {f.get('text_context', 'N/A')}\n\n"

prompt = f"""You are a Lead Regulatory Analyst for Affirm. 
Analyze the following policy findings and write a comprehensive, highly detailed Executive Report in Markdown format. 
Do not output JSON. Output ONLY clean Markdown with headers, bullet points, and tables.

Structure the report exactly like this:
# Affirm Regulatory Policy Analysis
## Executive Summary
## Regulatory Threat Matrix
## Operational Impact (Underwriting, Servicing, Marketing)
## Moat Analysis & Competitive Landscape
## Strategic Recommendations

Findings to analyze:
{findings_text}
"""

data = {
    "model": "nemotron:70b",
    "prompt": prompt,
    "stream": False,
    "options": {
        "num_predict": 4096,
        "temperature": 0.2
    }
}

req = urllib.request.Request(
    "http://localhost:11434/api/generate", 
    data=json.dumps(data).encode("utf-8"), 
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=600) as response:
        result = json.loads(response.read().decode("utf-8"))
        md_content = result.get("response", "")
        
        with open("FULL_AFFIRM_REPORT.md", "w") as f:
            f.write(md_content)
            
        print("🎉 Done! Report saved to FULL_AFFIRM_REPORT.md\n")
        print("="*60 + "\n")
        print(md_content)
        print("\n" + "="*60)
except Exception as e:
    print(f"❌ Error during generation: {e}")
finally:
    driver.close()
