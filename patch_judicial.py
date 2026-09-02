import sys

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    lines = f.readlines()

# 1. Add class variables after the class definition
for i, line in enumerate(lines):
    if line.strip().startswith('class JudicialMonitorAgent(BaseAgent):'):
        # Insert after this line
        lines.insert(i+1, '    SWARM_ID = "affirm_policy_swarm"\n')
        lines.insert(i+2, '    PROJECT_SCOPE = "affirm_bnpl_policy"\n')
        break

# 2. Update __init__ to set instance variables (optional)
for i, line in enumerate(lines):
    if line.strip().startswith('def __init__(self, agent_id: str = None, role: str = "Judicial Monitor Agent"):'):
        # Find the line where self.start_time is set (we know it's in the same method)
        for j in range(i, len(lines)):
            if 'self.start_time = time.time()' in lines[j]:
                # Insert after this line
                lines.insert(j+1, '        self.SWARM_ID = self.__class__.SWARM_ID\n')
                lines.insert(j+2, '        self.PROJECT_SCOPE = self.__class__.PROJECT_SCOPE\n')
                break
        break

# 3. Update the MERGE clause in the method that creates/updates the judicial record.
for i, line in enumerate(lines):
    if 'MERGE (j:JudicialCase {' in line:
        # We'll change the line to add swarm_id and project_scope.
        # The line currently is:
        #                MERGE (j:JudicialCase {
        #                    case_id: $case_id
        #                })
        # We want to change it to:
        #                MERGE (j:JudicialCase {
        #                    case_id: $case_id,
        #                    swarm_id: $swarm_id,
        #                    project_scope: $project_scope
        #                })
        # We'll do this by inserting two lines after the line with 'case_id: $case_id' and before the closing brace.
        # We'll find the line with the closing brace for this block.
        j = i
        while j < len(lines) and '                })' not in lines[j]:
            j += 1
        if j < len(lines):
            # Insert two lines before the line that has '                })'
            lines.insert(j, '                    swarm_id: $swarm_id,\n')
            lines.insert(j+1, '                    project_scope: $project_scope,\n')
        break

# 4. Update the parameters in the session.run call for the MERGE query.
# We need to add swarm_id and project_scope to the parameters.
# We'll look for the line that has: result = session.run(query, 
# and then we know the parameters are in the following lines until the closing parenthesis.
for i, line in enumerate(lines):
    if 'result = session.run(query,' in line:
        # We'll look ahead for the line with 'case_id=item['
        for j in range(i, len(lines)):
            if 'case_id=item[' in lines[j]:
                # We'll insert after the line that has the last parameter (which is timestamp=...)
                # But we don't know which is the last. We'll look for the line that has the closing parenthesis of the session.run call.
                # Actually, we can look for the line that has ')'
                k = j
                while k < len(lines) and ')' not in lines[k]:
                    k += 1
                if k < len(lines):
                    # We'll insert two lines before the line that has the closing parenthesis.
                    # But note: the last parameter line (timestamp=...) might not have a comma at the end? We'll add a comma to the previous line.
                    # We'll insert two lines with the same indentation as the parameter lines.
                    # Let's find the indentation of the first parameter line (case_id=item['...')
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    line1 = ' ' * indent + 'swarm_id=self.SWARM_ID,'
                    line2 = ' ' * indent + 'project_scope=self.PROJECT_SCOPE'
                    # Insert them before the line at index k (which is the line with the closing parenthesis)
                    lines.insert(k, line1 + '\n')
                    lines.insert(k+1, line2 + '\n')
                break
        break

# 5. Update the connect_query if it uses MATCH on the judicial node and we want to ensure we only match our swarm's nodes.
# We'll look for the MATCH in the connect_query.
for i, line in enumerate(lines):
    if 'MATCH (j {node_id: $node_id})' in line:
        # We'll change it to also match on swarm_id and project_scope? 
        # But note: the judicial node we just created has the swarm_id and project_scope.
        # We want to make sure we are only connecting to nodes that belong to our swarm.
        # So we change the MATCH to:
        #   MATCH (j {node_id: $node_id, swarm_id: $swarm_id, project_scope: $project_scope})
        lines[i] = line.replace('MATCH (j {node_id: $node_id})', 
                               'MATCH (j {node_id: $node_id, swarm_id: $swarm_id, project_scope: $project_scope})')
        break

# Write the file back
with open(file_path, 'w') as f:
    f.writelines(lines)

print(f"Patched {file_path}")
