import sys
sys.path.insert(0, '.')
from agents.regulatory_watch import RegulatoryWatchAgent
agent = RegulatoryWatchAgent('test')
print("Has browse_url?", hasattr(agent, 'browse_url'))
if hasattr(agent, 'browse_url'):
    print("Method:", agent.browse_url)
    # Try to call it
    try:
        result = agent.browse_url('https://httpbin.org/html')
        print("Result length:", len(result))
    except Exception as e:
        print("Error:", e)
else:
    print("Attributes:", [a for a in dir(agent) if not a.startswith('_')])
