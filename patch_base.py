import sys

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    lines = f.readlines()

# Add class variables after the class definition
# Find the class definition line
class_line_idx = -1
for i, line in enumerate(lines):
    if line.strip().startswith('class BaseAgent(abc.ABC):'):
        class_line_idx = i
        break

if class_line_idx != -1:
    # Insert after the class definition line and before the docstring if it exists on the next line.
    insert_at = class_line_idx + 1
    # If the next line starts with triple quotes, we want to insert after the docstring.
    if insert_at < len(lines) and lines[insert_at].strip().startswith('"""'):
        # Find the end of the docstring
        j = insert_at + 1
        while j < len(lines) and not lines[j].strip().endswith('"""'):
            j += 1
        if j < len(lines) and not lines[j].strip().endswith('"""'):
        j += 1  # after the closing triple quotes
    else:
        insert_at = class_line_idx + 1

    # Insert the class variables
    lines.insert(insert_at, '    SWARM_ID = "affirm_policy_swarm"\n')
    lines.insert(insert_at + 1, '    PROJECT_SCOPE = "affirm_bnpl_policy"\n')

# Now, we need to modify the __init__ method to set instance variables (optional but good for clarity)
# Find the __init__ method
init_start = -1
for i in range(len(lines)):
    if lines[i].strip().startswith('def __init__(self, agent_id: str = None, role: str = "BaseAgent"):'):
        init_start = i
        break

if init_start != -1:
    # Find the line where self.start_time is set (we know it's near the end of __init__)
    for i in range(init_start, len(lines)):
        if 'self.start_time = time.time()' in lines[i]:
            # Insert after this line
            lines.insert(i+1, '        self.SWARM_ID = self.__class__.SWARM_ID\n')
            lines.insert(i+2, '        self.PROJECT_SCOPE = self.__class__.PROJECT_SCOPE\n')
            break

# Now, we need to modify the query_graph_state and update_graph_state methods.
# We'll look for the MATCH and MERGE clauses and add swarm_id and project_scope.

# For query_graph_state: we need to change the MATCH to include swarm_id and project_scope.
for i in range(len(lines)):
    if 'MATCH (n:PolicyState {lookup_key: $lookup_key})' in lines[i]:
        lines[i] = lines[i].replace('MATCH (n:PolicyState {lookup_key: $lookup_key})', 
                                   'MATCH (n:PolicyState {lookup_key: $lookup_key, swarm_id: $swarm_id, project_scope: $project_scope})')
        break

# For update_graph_state: we need to change the MERGE to include swarm_id and project_scope.
for i in range(len(lines)):
    if 'MERGE (n:PolicyState {lookup_key: $lookup_key})' in lines[i]:
        lines[i] = lines[i].replace('MERGE (n:PolicyState {lookup_key: $lookup_key})', 
                                   'MERGE (n:PolicyState {lookup_key: $lookup_key, swarm_id: $swarm_id, project_scope: $project_scope})')
        break

# Now, we need to add the parameters to the session.run calls in both methods.
# For query_graph_state: we need to add swarm_id and project_scope to the parameters.
for i in range(len(lines)):
    if 'result = session.run(query, lookup_key=lookup_key)' in lines[i]:
        lines[i] = lines[i].replace('result = session.run(query, lookup_key=lookup_key)', 
                                   'result = session.run(query, lookup_key=lookup_key, swarm_id=self.SWARM_ID, project_scope=self.PROJECT_SCOPE)')
        break

# For update_graph_state: we need to add swarm_id and project_scope to the parameters.
for i in range(len(lines)):
    if 'result = session.run(query,' in lines[i] and 'lookup_key=lookup_key' in lines[i]:
        # We'll look for the line that has the parameters and add ours.
        # The line might be split, but we know the pattern from the file.
        # We'll do a simple replacement for the line we know.
        if 'lookup_key=lookup_key,' in lines[i] and 'data=json.dumps(data),' in lines[i]:
            lines[i] = lines[i].replace('lookup_key=lookup_key,', 
                                       'lookup_key=lookup_key, swarm_id=self.SWARM_ID, project_scope=self.PROJECT_SCOPE,')
        break

# Write the file back
with open(file_path, 'w') as f:
    f.writelines(lines)

print(f"Patched {file_path}")
