#!/bin/bash
WORKSPACE="$HOME/.openclaw/workspace/affirm_policy_swarm"
REPORT="swarm_audit_report.txt"

echo "========================================" > $REPORT
echo " OPENCLAW SWARM MASTER AUDIT REPORT" >> $REPORT
echo "========================================" >> $REPORT

echo -e "\n[1] MOCK DATA, TODOs, & PLACEHOLDERS" >> $REPORT
grep -rnw "$WORKSPACE" -E -i "mock|dummy|todo|fixme|placeholder|see connector config" --exclude-dir=__pycache__ --exclude-dir=.git --exclude="*.bak" --exclude="*backup*" >> $REPORT

echo -e "\n[2] HARDCODED URLS & ENDPOINTS" >> $REPORT
grep -rnw "$WORKSPACE" -E "http://|https://|bolt://" --exclude-dir=__pycache__ --exclude-dir=.git --exclude="*.bak" --exclude="*backup*" >> $REPORT

echo -e "\n[3] HARDCODED PORTS (Hunting 7687/7688/18789)" >> $REPORT
grep -rnw "$WORKSPACE" -E "7687|7688|18789" --exclude-dir=__pycache__ --exclude-dir=.git --exclude="*.bak" --exclude="*backup*" >> $REPORT

echo -e "\n[4] ACTIVE DOCKER CONTAINERS (Database Check)" >> $REPORT
docker ps -a >> $REPORT

echo -e "\n[5] EXACT ORCHESTRATOR LOGIC (agents/orchestrator.py)" >> $REPORT
cat "$WORKSPACE/agents/orchestrator.py" >> $REPORT

echo -e "\n[6] EXACT SOURCE REGISTRY (infrastructure/source_registry.py)" >> $REPORT
cat "$WORKSPACE/infrastructure/source_registry.py" >> $REPORT

echo -e "\nAudit complete. Saved to swarm_audit_report.txt."
