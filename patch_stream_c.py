import os

filepath = os.path.expanduser('~/.openclaw/workspace/affirm_policy_swarm/agents/orchestrator.py')
with open(filepath, 'r') as f:
    lines = f.readlines()

# 1. Insert Imports
import_idx = 0
for i, line in enumerate(lines):
    if "from agents.human_feedback_agent import HumanFeedbackAgent" in line:
        import_idx = i + 1
        break
lines.insert(import_idx, "from agents.market_sentiment_agent import MarketSentimentAgent\nfrom agents.public_statement_monitor_agent import PublicStatementMonitorAgent\n")

# 2. Insert Initialization
init_idx = 0
for i, line in enumerate(lines):
    if "human_feedback = HumanFeedbackAgent()" in line:
        init_idx = i + 1
        break
lines.insert(init_idx, "        market_sentiment = MarketSentimentAgent()\n        public_statement = PublicStatementMonitorAgent()\n")

# 3. Insert Stream C Execution
stream_c_idx = 0
for i, line in enumerate(lines):
    if "all_records.extend(api_records)" in line:
        stream_c_idx = i
        break

stream_c_code = """
        # 3. STREAM C: SENTIMENT & SOCIAL MONITORS
        logger.info(f"[{self.__class__.__name__}] Starting Stream C: Sentiment & Social Monitors")
        sentiment_records = []
        
        # 3a. Market Sentiment
        try:
            market_out = market_sentiment.execute_task({"type": "monitor_market_sentiment", "lookback_hours": 24})
            for item in market_out.get("analyzed_content", []):
                sentiment_records.append({
                    "title": item.get('title', 'Market Sentiment'),
                    "snippet": f"Sentiment Score: {item.get('sentiment_score', 0)} | Phrases: {', '.join(item.get('key_phrases', []))}",
                    "source": item.get('source', 'Unknown Market Source'),
                    "url": item.get('url', ''),
                    "date": item.get('published', '')
                })
            logger.info(f"[{self.__class__.__name__}] Market Sentiment: Collected {len(market_out.get('analyzed_content', []))} records")
        except Exception as e:
            logger.error(f"Market Sentiment Monitor failed: {e}")

        # 3b. Public Statements
        try:
            statement_out = public_statement.execute_task({"run_id": run_id})
            for item in statement_out.get("records", []):
                sentiment_records.append({
                    "title": item.get('title', 'Public Statement'),
                    "snippet": item.get('text_context', ''),
                    "source": item.get('source', 'Social Monitor'),
                    "url": "",
                    "date": ""
                })
            logger.info(f"[{self.__class__.__name__}] Public Statements: Collected {len(statement_out.get('records', []))} records")
        except Exception as e:
            logger.error(f"Public Statement Monitor failed: {e}")
            
        all_records.extend(sentiment_records)
"""
lines.insert(stream_c_idx, stream_c_code)

with open(filepath, 'w') as f:
    f.writelines(lines)

print("Stream C successfully injected into Orchestrator.")
