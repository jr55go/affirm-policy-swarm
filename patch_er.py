path = 'agents/entity_resolution_agent.py'
with open(path, 'r') as f:
    lines = f.readlines()

with open(path, 'w') as f:
    for line in lines:
        f.write(line)
        if 'class EntityResolutionAgent' in line:
            f.write('    name = "EntityResolutionAgent"\n')

print("EntityResolutionAgent successfully patched.")
