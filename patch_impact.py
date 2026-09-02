import sys

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    lines = f.readlines()

# 1. Add class variables after the class definition
for i, line in enumerate(lines):
    if line.strip().startswith('class ImpactAnalyzerAgent(BaseAgent):'):
        # Insert after this line
        lines.insert(i+1, '    SWARM_ID = "affirm_policy_swarm"\n')
        lines.insert(i+2, '    PROJECT_SCOPE = "affirm_bnpl_policy"\n')
        break

# 2. Update __init__ to set instance variables (optional)
for i, line in enumerate(lines):
    if line.strip().startswith('def __init__(self, agent_id: str = None, role: str = "Impact Analyzer Agent"):'):
        # Find the line where self.start_time is set (we know it's in the same method)
        for j in range(i, len(lines)):
            if 'self.start_time = time.time()' in lines[j]:
                # Insert after this line
                lines.insert(j+1, '        self.SWARM_ID = self.__class__.SWARM_ID\n')
                lines.insert(j+2, '        self.PROJECT_SCOPE = self.__class__.PROJECT_SCOPE\n')
                break
        break

# 3. Update the MERGE clause to include swarm_id and project_scope
for i, line in enumerate(lines):
    if 'MERGE (n:ImpactAnalysis {policy_id: $policy_id, jurisdiction: $jurisdiction})' in line:
        # Change to:
        # MERGE (n:ImpactAnalysis {policy_id: $policy_id, jurisdiction: $jurisdiction, swarm_id: $swarm_id, project_scope: $project_scope})
        lines[i] = line.replace('MERGE (n:ImpactAnalysis {policy_id: $policy_id, jurisdiction: $jurisdiction})',
                               'MERGE (n:ImpactAnalysis {policy_id: $policy_id, jurisdiction: $jurisdiction, swarm_id: $swarm_id, project_scope: $project_scope})')
        break

# 4. Update the session.run call to include the swarm_id and project_scope parameters
for i, line in enumerate(lines):
    if 'result = session.run(query,' in line:
        # We'll look for the line that has the parameters and add ours.
        # We know the parameters are in the following lines until the closing parenthesis.
        # We'll do a simple approach: we'll look for the line that has the closing parenthesis of the session.run call and insert before it.
        j = i
        while j < len(lines) and ')' not in lines[j]:
            j += 1
        if j < len(lines):
            # We'll insert two lines before the line at index j.
            # But we need to know the indentation of the parameter lines.
            # We'll look at the line after the 'result = session.run(query,' line to get the indentation.
            if i+1 < len(lines):
                indent = len(lines[i+1]) - len(lines[i+1].lstrip())
                line1 = ' ' * indent + 'swarm_id=self.SWARM_ID,'
                line2 = ' ' * indent + 'project_scope=self.PROJECT_SCOPE'
                # Insert these two lines before the line at index j
                lines.insert(j, line1 + '\n')
                lines.insert(j+1, line2 + '\n')
            break

# Write the file back
with open(file_path, 'w') as f:
    f.writelines(lines)

print(f"Patched {file_path}")
