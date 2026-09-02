import sys
import re

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    content = f.read()

# Add class variables SWARM_ID and PROJECT_SCOPE
# Find the class definition and insert after the docstring or before __init__
# We'll do a simple approach: insert after the class line if we don't find a better spot.

# First, let's add the class variables.
# We'll look for the line with 'class RegulatoryWatchAgent' and then insert after the next line that is not a comment or empty.
# But for simplicity, we'll insert after the class line and before the first method.

lines = content.split('\n')
new_lines = []
inserted_class_vars = False
for i, line in enumerate(lines):
    new_lines.append(line)
    if line.strip().startswith('class RegulatoryWatchAgent') and not inserted_class_vars:
        # We'll insert the class variables after the class line, but before the docstring or the first method.
        # We'll look ahead to see if the next line is a docstring.
        j = i + 1
        while j < len(lines) and (lines[j].strip().startswith('\"\"\"') or lines[j].strip() == '' or lines[j].strip().startswith('#')):
            j += 1
        # Now insert at position j (which is the first non-comment, non-empty line after the class line)
        # But we are building the list sequentially, so we'll insert after we've processed the class line.
        # We'll add the lines now and then skip the ones we've already processed? 
        # Instead, let's just insert after the class line and then adjust the index.
        # We'll do: insert after the class line, then continue.
        # We'll add the two lines and then set a flag so we don't add again.
        new_lines.append('    SWARM_ID = "affirm_policy_swarm"')
        new_lines.append('    PROJECT_SCOPE = "affirm_bnpl_policy"')
        inserted_class_vars = True

# Now join the lines back
content = '\n'.join(new_lines)

# Now update the MERGE clause in the RegulatoryMonitoring creation.
# We'll look for the MERGE (r:RegulatoryMonitoring { ... }) pattern and add swarm_id and project_scope.

# We'll do two steps: 
# 1. Add the properties to the MERGE pattern.
# 2. Add the parameters to the session.run call.

# First, let's find the MERGE line and the properties inside the braces.
# We'll use a regex to capture the MERGE statement and then insert the two properties.

# Pattern for the MERGE line (we know it's in the regulatory_watch.py file)
# We'll look for: 
#                MERGE (r:RegulatoryMonitoring {
#                    jurisdiction: $jurisdiction,
#                    product: $product,
#                    monitoring_period: $period
#                })
# and change to:
#                MERGE (r:RegulatoryMonitoring {
#                    jurisdiction: $jurisdiction,
#                    product: $product,
#                    monitoring_period: $period,
#                    swarm_id: $swarm_id,
#                    project_scope: $project_scope
#                })

# We'll do a regex that matches from MERGE (r:RegulatoryMonitoring { to the closing })
# but we'll do it in a more targeted way.

# We'll break the content into lines and process.

lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Look for the line that starts with '                MERGE (r:RegulatoryMonitoring {'
    if line.strip().startswith('MERGE (r:RegulatoryMonitoring {'):
        # We'll add this line and then the next lines until we find the closing brace.
        # But we want to insert two lines before the closing brace.
        # We'll collect the lines until we find the line that has '                })'
        block_lines = [line]
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith('})'):
            block_lines.append(lines[j])
            j += 1
        if j < len(lines):
            block_lines.append(lines[j])  # the closing brace line
            # Now we have the block from i to j (inclusive)
            # We want to insert two lines before the last line (the closing brace)
            # The last line is block_lines[-1]
            # We'll insert two lines: 
            #                     swarm_id: $swarm_id,
            #                     project_scope: $project_scope
            # with the same indentation as the other lines.
            # Let's get the indentation of the first property line (if any) or assume 20 spaces.
            # We'll look at the second line in the block (index 1) for indentation.
            if len(block_lines) >= 2:
                # The second line is the first property line.
                indent = len(block_lines[1]) - len(block_lines[1].lstrip())
                # We'll create the two lines with that indentation.
                line1 = ' ' * indent + 'swarm_id: $swarm_id,'
                line2 = ' ' * indent + 'project_scope: $project_scope'
                # Insert them before the last line
                block_lines = block_lines[:-1] + [line1, line2, block_lines[-1]]
            else:
                # If there are no properties, we just add the two lines before the closing brace.
                # But we know there are properties.
                pass
            # Now replace the lines in the main list
            new_lines.extend(block_lines)
            i = j + 1
            continue
    else:
        new_lines.append(line)
        i += 1

content = '\n'.join(new_lines)

# Now we need to update the session.run call to include the swarm_id and project_scope parameters.
# We'll look for the session.run call for the MERGE query.
# We'll do a similar line-by-line approach.

lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Look for the line that has: result = session.run(query, 
    # and then we know the parameters are in the following lines until the closing brace.
    if 'result = session.run(query, ' in line:
        # We'll collect the lines until we find the closing brace of the parameter dictionary.
        # We'll start with the current line and then go forward.
        param_lines = [line]
        j = i + 1
        while j < len(lines) and not lines[j].strip().endswith(')'):
            param_lines.append(lines[j])
            j += 1
        if j < len(lines):
            param_lines.append(lines[j])  # the line with the closing parenthesis
            # Now we have the parameter lines from i to j (inclusive)
            # We want to insert two lines before the last line (the closing parenthesis line)
            # But note: the last line might be just a closing parenthesis on its own, or it might be part of the same line as the last parameter.
            # We'll look for the line that has the closing parenthesis of the session.run call.
            # Actually, the pattern is:
            #                result = session.run(query, 
            #                                   jurisdiction=jurisdiction,
            #                                   product=product,
            #                                   monitoring_period=f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')} (24h)",
            #                                   items_count=len(self._fetch_regulatory_data(jurisdiction, product, 24, self._get_default_agencies(jurisdiction))),  # This would be cached in reality
            #                                   relevant_count=len(analyzed_items),
            #                                   analysis_data=json.dumps(analyzed_items)
            #                                 )
            # We want to insert before the closing parenthesis that is on its own line (the last line above).
            # We'll add two lines with the same indentation as the parameter lines.
            # Let's find the indentation of the first parameter line (index 1 in param_lines).
            if len(param_lines) >= 2:
                # The second line is the first parameter.
                indent = len(param_lines[1]) - len(param_lines[1].lstrip())
                # We'll create the two lines.
                line1 = ' ' * indent + 'swarm_id=self.SWARM_ID,'
                line2 = ' ' * indent + 'project_scope=self.PROJECT_SCOPE'
                # Insert them before the last line (which is the line with the closing parenthesis)
                # But note: the last line might be the closing parenthesis line, or it might be the last parameter and then the closing parenthesis.
                # We'll look at the last line: if it contains only whitespace and a closing parenthesis, then we insert before it.
                # Otherwise, we assume the last line is the last parameter and we need to add a comma and then insert on new lines.
                # We'll keep it simple: we'll insert before the last line and then adjust the last line if needed.
                # We'll remove the last line, add our two lines, then add the last line back.
                # But we must ensure that the line before the last line (which will be the last parameter) ends with a comma.
                # Let's check the second last line (which will be the last parameter after we insert).
                # We'll just insert the two lines and then the last line, and rely on the existing comma in the last parameter line.
                # Actually, the last parameter line (relevant_count=len(analyzed_items),) already has a comma.
                # So we can do:
                new_param_lines = param_lines[:-1] + [line1, line2, param_lines[-1]]
            else:
                # If there are no parameters, we just add the two lines and then the closing parenthesis.
                # But we know there are parameters.
                new_param_lines = param_lines[:-1] + [line1, line2, param_lines[-1]]
            # Now replace the lines in the main list
            new_lines.extend(new_param_lines)
            i = j + 1
            continue
    else:
        new_lines.append(line)
        i += 1

content = '\n'.join(new_lines)

# Write back
with open(file_path, 'w') as f:
    f.write(content)

print(f"Patched {file_path}")
