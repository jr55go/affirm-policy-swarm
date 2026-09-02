import os
import sys
import traceback

from agents.legislative_monitor import LegislativeMonitorAgent


def fail(msg):
    print(f"connector test result: FAILED")
    print(f"reason: {msg}")
    sys.exit(2)


def main():
    agent = LegislativeMonitorAgent()

    print("Congress.gov endpoint family used: /v3/bill/{congress}/{billType}")
    print("Congress.gov congress used: 119")
    print("Congress.gov bill types tested: hr,s,hjres,sjres,hconres,sconres,hres,sres")
    print("LegiScan op used: getSearch")
    print("LegiScan state used: ALL")

    try:
        congress_results = agent._search_congress_gov_bills("buy now pay later", congress=119, limit=5)
        print(f"Congress.gov records returned: {len(congress_results)}")
    except Exception as e:
        fail(f"Congress.gov connector failed: {e}")

    try:
        legiscan_results = agent._search_legiscan_bills("buy now pay later", state="ALL")
        print(f"LegiScan records returned: {len(legiscan_results)}")
    except Exception as e:
        fail(f"LegiScan connector failed: {e}")

    try:
        res = agent.execute_task({
            "type": "legislative_monitoring",
            "jurisdiction": "US Federal",
            "product": "buy_now_pay_later",
            "lookback_hours": 720,
            "swarm_id": "affirm_policy_swarm",
            "project_scope": "affirm_bnpl_policy",
        })
        print(f"LegislativeMonitorAgent status: {res.get('status')}")
        print(f"Legislative items found: {res.get('legislative_items_found')}")
        print(f"Relevant items: {res.get('relevant_items')}")
        print(f"Analyzed items length: {len(res.get('analyzed_items', []))}")
    except Exception as e:
        fail(f"Legislative monitor task failed: {e}")

    print("connector test result: PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(2)
