agent_path = 'agents/validation_agent.py'
with open(agent_path, 'r') as f:
    content = f.read()

if "self.name =" not in content:
    content = content.replace(
        'super().__init__(agent_id, role="Validation Agent")',
        'super().__init__(agent_id, role="Validation Agent")\n        self.name = "Validation Agent"'
    )
    with open(agent_path, 'w') as f:
        f.write(content)
    print("Patched ValidationAgent with self.name attribute.")
