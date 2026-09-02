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
                lines.insert(j+2, '        self.PROJECT_SCOPE = self.__class__.PROJECT_SCOPE\n')
                break
        break

# 3. Update query_graph_state method: change the MATCH and add parameters
for i, line in enumerate(lines):
    if 'MATCH (n:PolicyState {lookup_key: $lookup_key})' in line:
        lines[i] = line.replace('MATCH (n:PolicyState {lookup_key: $lookup_key})', 
                               'MATCH (n:PolicyState {lookup_key: $lookup_key, swarm_id: $swarm_id, project_scope: $project_scope})')
        break

# 4. Update the session.run call in query_graph_state
for i, line in enumerate(lines):
    if 'result = session.run(query, lookup_key=lookup_key)' in line:
        lines[i] = line.replace('result = session.run(query, lookup_key=lookup_key)', 
                               'result = session.run(query, lookup_key=lookup_key, swarm_id=self.SWARM_ID, project_scope=self.PROJECT_SCOPE)')
        break

# 5. Update update_graph_state method: change the MERGE and add parameters
for i, line in enumerate(lines):
    if 'MERGE (n:PolicyState {lookup_key: $lookup_key})' in line:
        lines[i] = line.replace('MERGE (n:PolicyState {lookup_key: $lookup_key})', 
                               'MERGE (n:PolicyState {lookup_key: $lookup_key, swarm_id: $swarm_id, project_scope: $project_scope})')
        break

# 6. Update the session.run call in update_graph_state
# We need to find the line that has the parameters and add ours.
# We know the line looks like:
#                result = session.run(query,
#                                   lookup_key=lookup_key,
#                                   data=json.dumps(data),
#                                   updated_at=datetime.now(timezone.utc).isoformat(),
#                                   version=new_version)
# We'll insert our parameters after the lookup_key line.
for i, line in enumerate(lines):
    if 'result = session.run(query,' in line:
        # We'll look ahead for the line with 'lookup_key=lookup_key,'
        for j in range(i, len(lines)):
            if 'lookup_key=lookup_key,' in lines[j]:
                # Insert after this line
                lines.insert(j+1, '                                   swarm_id=self.SWARM_ID,\n')
                lines.insert(j+2, '                                   project_scope=self.PROJECT_SCOPE,\n')
                break
        break

# Write the file back
with open(file_path, 'w') as f:
    f.writelines(lines)

print(f"Patched {file_path}")
