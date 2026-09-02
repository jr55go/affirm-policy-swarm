import os
import json
from agents.research_synthesis_agent import ResearchSynthesisAgent
from agents.reporting_agent import ReportingAgent

def main():
    print("🚀 Firing Astrada-Tier Reporting Pipeline Verification Test...")
    print("------------------------------------------------------------")

    # 1. High-Signal Mock Findings (NY DFS + CA DFPI + 1 Rejected SEO Noise item)
    mock_findings = [
        {
            "id": "NODE_NY_DFS_423",
            "title": "NY DFS Proposed Rule Part 423: BNPL Licensing and $8 Late Fee Cap",
            "compressed_summary": "New York DFS proposed Part 423 under Banking Law Article 14-B. Mandates state-level licensing, strict $8 cap on late fees, 16% interest rate cap, and credit-card-style billing dispute mechanisms.",
            "text_context": "Detailed breakdown of NY DFS Part 423 rulemaking...",
            "jurisdiction": "New York",
            "impact_score": "high",
            "policy_risk_score": 92,
            "validation_status": "approved",
            "source": "New York DFS Portal",
            "url": "https://www.dfs.ny.gov/reports_and_publications/press_releases",
            "inferred_market_impact": "Imposes mandatory state licensing and caps late fees at $8. Alters unit economics for fee-dependent BNPL platforms."
        },
        {
            "id": "NODE_CA_DFPI_CFL",
            "title": "CA DFPI Consumer Protection Notice: California Financing Law Compliance for POS Lenders",
            "compressed_summary": "California DFPI actively bringing all point-of-sale and Buy Now, Pay Later providers under the umbrella of the California Financing Law (CFL).",
            "text_context": "DFPI enforcement notice regarding POS licensing requirements...",
            "jurisdiction": "California",
            "impact_score": "high",
            "policy_risk_score": 85,
            "validation_status": "approved",
            "source": "California DFPI News Feed",
            "url": "https://dfpi.ca.gov/news/",
            "inferred_market_impact": "Forces BNPL providers to obtain CFL licensing and submit to state examinations and dispute rules."
        },
        {
            "id": "NODE_SEO_NOISE_1",
            "title": "Lawfold Blog: Top 5 Personal Injury Lawyers in Queens",
            "compressed_summary": "Generic SEO lawyer blog farm content.",
            "impact_score": "low",
            "policy_risk_score": 15,
            "validation_status": "rejected",
            "validation_reason": "Rejected by ValidationAgent (Low Relevance / Consumer SEO Noise).",
            "source": "lawfold.com",
            "url": "https://lawfold.com/queens-lawyers"
        }
    ]

    # 2. Run Synthesis Agent (nemotron:70b extracts Astrada-Tier JSON)
    print("\n🧠 [Phase 1] Executing Research Synthesis Agent...")
    synthesis_agent = ResearchSynthesisAgent()
    synthesis_result = synthesis_agent.execute_task({"findings": mock_findings})
    
    print("\n🔍 Synthesized Keys Extracted:")
    for key, val in synthesis_result.items():
        print(f"  • {key}: {str(val)[:80]}...")

    # 3. Run Reporting Agent (Renders Executive Markdown)
    print("\n📊 [Phase 2] Executing Reporting Agent...")
    reporting_agent = ReportingAgent()
    test_dir = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm/reports/test_run")
    result = reporting_agent.execute_task({
        "report_dir": test_dir,
        "findings": mock_findings,
        "synthesis": synthesis_result
    })

    report_path = result.get("report_path")
    print(f"\n✅ Report compiled successfully at: {report_path}\n")
    
    # 4. Print Compiled Report
    print("======================== GENERATED EXECUTIVE BRIEF ========================\n")
    with open(report_path, "r", encoding="utf-8") as f:
        print(f.read())
    print("===========================================================================")

if __name__ == "__main__":
    main()
