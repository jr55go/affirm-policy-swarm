import sys

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    lines = f.readlines()

# Find the update_graph_state method and the session.run call within it.
for i, line in enumerate(lines):
    if 'def update_graph_state(self, lookup_key: str, data: Dict[str, Any]) -> bool:' in line:
        # Now look for the line with 'result = session.query(query,' within this method.
        for j in range(i, len(lines)):
            if 'result = session.run(query,' in lines[j]:
                # We found the line. Now we need to insert the two parameters before the closing parenthesis.
                # Let's find the line that has the closing parenthesis of this call.
                k = j
                while k < len(lines) and ')' not in lines[k]:
                    k += 1
                if k < len(lines):
                    # We'll insert two lines before the line at index k.
                    # But we need to know the indentation of the parameter lines.
                    # Look at the line after the 'result = session.run(query,' line.
                    if j+1 < len(lines):
                        param_line = lines[j+1]
                        indent = len(param_line) - len(param_line.lstrip())
                        line1 = ' ' * indent + 'swarm_id=self.SWARM_ID,\n'
                        line2 = ' ' * indent + 'project_scope=self.PROJECT_SCOPE\n'
                        # Insert these two lines at position k (so they become lines k and k+1, and the old line k moves down)
                        lines.insert(k, line1)
                        lines.insert(k+1, line2)
                break
        break

with open(file_path, 'w') as f:
    f.writelines(lines)

print(f"Patched {file_path}")
