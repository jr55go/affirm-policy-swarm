import sys
sys.path.insert(0, '.')

# Create a simple test agent that inherits from BaseAgent
from agents.base_agent import BaseAgent

class TestAgent(BaseAgent):
    def __init__(self, agent_id=None):
        super().__init__(agent_id or "test-agent", "TestAgent")
    
    def execute_task(self, task_data):
        return {"status": "test"}
    
    def get_capabilities(self):
        return ["test"]

# Test the browse_url method
agent = TestAgent()
print("TestAgent has browse_url?", hasattr(agent, 'browse_url'))
if hasattr(agent, 'browse_url'):
    print("Method found:", agent.browse_url)
    # Test with a simple URL
    try:
        result = agent.browse_url('https://httpbin.org/html')
        print("Browse result length:", len(result))
        print("Preview:", result[:100])
    except Exception as e:
        print("Error during browse:", str(e)[:100])
else:
    print("Method NOT found")
    print("Available methods:", [m for m in dir(agent) if not m.startswith('_')])
