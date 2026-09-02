import sys

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    lines = f.readlines()

# 1. Add class variables after the class definition
for i, line in enumerate(lines):
    if line.strip().startswith('class BaseAgent(abc.ABC):'):
        # Insert after this line
        lines.insert(i+1, '    SWARM_ID = "affirm_policy_swarm"\n')
        lines.insert(i+2, '    PROJECT_SCOPE = "affirm_bnpl_policy"\n')
        break

# 2. Update __init__ to set instance variables
for i, line in enumerate(lines):
    if line.strip().startswith('def __init__(self, agent_id: str = None, role: str = "BaseAgent"):'):
        # Find the line where self.start_time is set (we know it's in the same method)
        for j in range(i, len(lines)):
            if 'self.start_time = time.time()' in lines[j]:
                # Insert after this line
                lines.insert(j+1, '        self.SWARM_ID = self.__class__.SWARM_ID\n')
                lines.insert(j+2, '        self.PROJECT_SCOPE = self.PROJECT_SCOPE = self.__class__.PROJECT_SCOPE\n')
                break
        break

# 3. Update query_graph_state method
# We need to change the MATCH line and the session.run call.
for i, line in enumerate(lines):
    if 'MATCH (n:PolicyState {lookup_key: $lookup_key})' in line:
        lines[i] = line.replace('MATCH (n:PolicyState {lookup_key: $lookup_key})', 
                               'MATCH (n:PolicyState {lookup_key: $lookup_key, swarm_id: $swarm_id, project_scope: $project_scope})')
        break

# Now find the session.run call in the same method and add the parameters.
# We'll look for the line that has: result = session.run(query, lookup_key=lookup_key)
for i, line in enumerate(lines):
    if 'result = session.run(query, lookup_key=lookup_key)' in line:
        lines[i] = line.replace('result = session.run(query, lookup_key=lookup_key)', 
                               'result = session.run(query, lookup_key=lookup_key, swarm_id=self.SWARM_ID, project_scope=self.PROJECT_SCOPE)')
        break

# 4. Update update_graph_state method
# Change the MERGE line
for i, line in enumerate(lines):
    if 'MERGE (n:PolicyState {lookup_key: $lookup_key})' in line:
        lines[i] = line.replace('MERGE (n:PolicyState {lookup_key: $lookup_key})', 
                               'MERGE (n:PolicyState {lookup_key: $lookup_key, swarm_id: $swarm_id, project_scope: $project_scope})')
        break

# Now find the session.run call in the update_graph_state method and add the parameters.
# We'll look for the line that has: result = session.run(query,
# and then we need to add the parameters in the parameter dictionary.
# We'll do a more targeted approach: we know the parameter lines are between the opening brace and the closing brace.
# We'll find the line with 'result = session.run(query,' and then look for the line with the closing brace of the parameter dict.
# But to keep it simple, we'll just insert two lines before the line that has the closing parenthesis of the session.run call.
# We'll search for the pattern: 'result = session.run(query,' and then assume the parameters are in the following lines until a line that contains '})' (if the dict is on multiple lines) or ')' (if on one line).
# Given the original code, the parameters are on multiple lines.
# We'll look for the line that has 'result = session.run(query,' and then we'll insert our parameters after the line that has 'version=new_version' (the last parameter).
# Let's do it by finding the line with 'version=new_version' and then inserting after it.

for i, line in enumerate(lines):
    if 'result = session.run(query,' in line:
        # Now look ahead for the line that contains 'version=new_version'
        for j in range(i, len(lines)):
            if 'version=new_version' in lines[j]:
                # Insert after this line
                # We need to know the indentation of this line to match.
                indent = len(lines[j]) - len(lines[j].lstrip())
                lines.insert(j+1, ' ' * indent + 'swarm_id=self.SWARM_ID,\n')
                lines.insert(j+2, ' ' * indent + 'project_scope=self.PROJECT_SCOPE\n')
                break
        break

# Write the file back
with open(file_path, 'w') as f:
    f.writelines(lines)

print(f"Patched {file_path}")
