import sys

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    lines = f.readlines()

# We'll fix the two CREATE statements.

# First, find the LegislativeMonitorRun CREATE and remove the trailing comma after project_scope.
# We know the pattern: after the line with "project_scope: $project_scope," there is a line with "                })"
# We want to remove the comma at the end of the line with "project_scope: $project_scope,"

for i, line in enumerate(lines):
    if 'project_scope: $project_scope,' in line:
        # Remove the trailing comma
        lines[i] = line.replace('project_scope: $project_scope,', 'project_scope: $project_scope')
        break

# Second, find the LegislativeItem CREATE and remove the trailing comma after swarm_id.
for i, line in enumerate(lines):
    if 'swarm_id: $swarm_id,' in line and 'LegislativeItem' in ''.join(lines[max(0, i-10):i+10]):
        # Remove the trailing comma
        lines[i] = line.replace('swarm_id: $swarm_id,', 'swarm_id: $swarm_id')
        break

# Write back
with open(file_path, 'w') as f:
    f.writelines(lines)

print(f"Fixed syntax in {file_path}")
