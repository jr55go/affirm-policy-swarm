import sys

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    lines = f.readlines()

# 1. Add class variables after the class definition
for i, line in enumerate(lines):
    if line.strip().startswith('class MarketSentimentAgent(BaseAgent):'):
        # Insert after this line
        lines.insert(i+1, '    SWARM_ID = "affirm_policy_swarm"\n')
        lines.insert(i+2, '    PROJECT_SCOPE = "affirm_bnpl_policy"\n')
        break

# 2. Update __init__ to set instance variables (optional)
for i, line in enumerate(lines):
    if line.strip().startswith('def __init__(self, agent_id: str = None):'):
        # Find the line where super().__init__ is called (we know it's in the same method)
        for j in range(i, len(lines)):
            if 'super().__init__(agent_id or f"market-sent-{str(uuid.uuid4())[:8]}", "Market Sentiment Agent")' in lines[j]:
                # Insert after this line
                lines.insert(j+1, '        self.SWARM_ID = self.__class__.SWARM_ID\n')
                lines.insert(j+2, '        self.PROJECT_SCOPE = self.__class__.PROJECT_SCOPE\n')
                break
        break

# 3. Update the MERGE clause for node creation (News and Social nodes)
# We'll update the MERGE line to include swarm_id and project_scope in the pattern.
# We'll also need to add the parameters to the session.run call.
# We'll do this by processing the lines and replacing the specific MERGE block.
# We know the MERGE line looks like:
#                     query = f"""
#                     MERGE (n:{node_type} {{
#                         content_id: $content_id,
#                         url: $url
#                     }})
# We want to change it to:
#                     MERGE (n:{node_type} {{
#                         content_id: $content_id,
#                         url: $url,
#                         swarm_id: $swarm_id,
#                         project_scope: $project_scope
#                     }})
# We'll do a string replacement for the entire MERGE block? It's easier to do line by line.
# We'll look for the line that contains 'MERGE (n:{node_type} {{'
# and then we know the next two lines are the content_id and url lines, and then the closing brace.
# We'll insert two lines after the url line and before the closing brace.

# We'll also need to update the parameters in the session.run call that follows.
# We'll look for the line that starts with '                    result = session.run(query,'
# and then we know the parameters are in the following lines until the closing parenthesis.

# We'll do a simple approach: we'll replace the MERGE block and then adjust the parameters.

# First, let's change the MERGE block.
for i, line in enumerate(lines):
    if 'MERGE (n:{node_type} {' in line:
        # We found the MERGE line.
        # We'll change the line to add swarm_id and project_scope in the mapping.
        # The line is:                     MERGE (n:{node_type} {
        # We want to change it to:                     MERGE (n:{node_type} {
        #                         content_id: $content_id,
        #                         url: $url,
        #                         swarm_id: $swarm_id,
        #                         project_scope: $project_scope
        #                     })
        # But note: the line might have indentation. We'll keep the indentation.
        # We'll replace the line with the same indentation plus the two new lines.
        # Actually, we cannot do it in one line because we are adding two new properties need to be on separate lines.
        # We'll break the MERGE line and insert the two new lines after the url line.
        # Let's assume the structure is:
        #                     MERGE (n:{node_type} {
        #                         content_id: $content_id,
        #                         url: $url
        #                     })
        # We'll change it to:
        #                     MERGE (n:{node_type} {
        #                         content_id: $content_id,
        #                         url: $url,
        #                         swarm_id: $swarm_id,
        #                         project_scope: $project_scope
        #                     })
        # We'll do:
        #   Keep the MERGE line as is.
        #   Then we look at the next line: it should be the content_id line.
        #   Then the next line after that is the url line.
        #   We'll insert two lines after the url line (before the closing brace line).
        #   We'll also need to add a comma at the end of the url line.
        #
        # Let's get the indentation of the MERGE line.
        indent = len(line) - len(line.lstrip())
        # The next line should be the content_id line.
        if i+1 < len(lines) and 'content_id: $content_id' in lines[i+1]:
            # The line after that should be the url line.
            if i+2 < len(lines) and 'url: $url' in lines[i+2]:
                # We'll add a comma to the end of the url line (if not already there)
                url_line = lines[i+2]
                if not url_line.rstrip().endswith(','):
                    lines[i+2] = url_line.rstrip() + ',\n'
                # Now insert two lines after the url line.
                lines.insert(i+3, ' ' * (indent + 4) + 'swarm_id: $swarm_id,\n')
                lines.insert(i+4, ' ' * (indent + 4) + 'project_scope: $project_scope\n')
                # We also need to adjust the closing brace line? It should remain the same.
                break

# 4. Update the parameters in the session.run call for the MERGE query.
# We'll look for the line that starts with '                    result = session.run(query,'
# and then we'll add the two parameters after the existing ones.
for i, line in enumerate(lines):
    if 'result = session.run(query,' in line:
        # We'll look ahead for the line that has the last parameter (which ends with a comma) and then the closing parenthesis.
        # We know the parameters are in the following lines until we see a line that has just a closing parenthesis.
        # We'll insert two lines before the line that has the closing parenthesis.
        j = i
        while j < len(lines) and ')' not in lines[j]:
            j += 1
        if j < len(lines):
            # We'll insert two lines before the line at index j.
            # We need to know the indentation of the parameter lines.
            # Look at the line after the 'result = session.run(query,' line.
            if i+1 < len(lines):
                param_line = lines[i+1]
                indent = len(param_line) - len(param_line.lstrip())
                line1 = ' ' * indent + 'swarm_id=$swarm_id,'
                line2 = ' ' * indent + 'project_scope=$project_scope'
                # Insert these two lines before the line at index j.
                lines.insert(j, line1 + '\n')
                lines.insert(j+1, line2 + '\n')
        break

# 5. Update any MATCH clauses that read these nodes to include swarm_id and project_scope.
# We need to find any MATCH that matches on content_id and url (or the node we just changed) and add swarm_id and project_scope.
# We'll look for lines that contain 'MATCH (n:{node_type} {{' or similar.
# We'll do a similar approach as for the MERGE.
for i, line in enumerate(lines):
    if 'MATCH (n:{node_type} {' in line:
        # We'll change the MATCH to include swarm_id and project_scope in the pattern.
        # We'll assume the same structure as the MERGE we just changed.
        # We'll add swarm_id and project_scope after the url line.
        # We'll look for the next two lines (content_id and url) and then insert after the url line.
        if i+1 < len(lines) and 'content_id: $content_id' in lines[i+1]:
            if i+2 < len(lines) and 'url: $url' in lines[i+2]:
                # Add a comma to the url line if not present
                url_line = lines[i+2]
                if not url_line.rstrip().endswith(','):
                    lines[i+2] = url_line.rstrip() + ',\n'
                # Insert two lines after the url line
                indent = len(line) - len(line.lstrip())
                lines.insert(i+3, ' ' * (indent + 4) + 'swarm_id: $swarm_id,\n')
                lines.insert(i+4, ' ' * (indent + 4) + 'project_scope: $project_scope\n')
        break

# 6. Also, we need to update the parameters in the session.run call for the MATCH query (if any) to include swarm_id and project_scope.
# But note: the MATCH query might be in a different context (like a verification query). We'll look for session.run calls after a MATCH.
# We'll do a simple approach: we'll look for any session.run call that is near a MATCH we just changed and add the parameters.
# However, to keep it simple, we'll assume that any session.run call that uses the same parameters (content_id, url) should also get swarm_id and project_scope.
# We'll look for session.run calls that have content_id and url in the parameters and add swarm_id and project_scope.
# We'll do this by scanning for session.run lines and then checking the parameters.

# We'll do a separate pass for session.run lines that have content_id and url.
for i, line in enumerate(lines):
    if 'session.run(' in line and 'content_id' in line and 'url' in line:
        # We'll look ahead for the closing parenthesis of the session.run call.
        j = i
        while j < len(lines) and ')' not in lines[j]:
            j += 1
        if j < len(lines):
            # We'll insert two lines before the line at index j.
            # We need to know the indentation of the parameter lines.
            # Look at the line after the 'session.run(' line.
            if i+1 < len(lines):
                param_line = lines[i+1]
                indent = len(param_line) - len(param_line.lstrip())
                line1 = ' ' * indent + 'swarm_id=$swarm_id,'
                line2 = ' ' * indent + 'project_scope=$project_scope'
                # Insert these two lines before the line at index j.
                lines.insert(j, line1 + '\n')
                lines.insert(j+1, line2 + '\n')
        break

# Write the file back
with open(file_path, 'w') as f:
    f.writelines(lines)

print(f"Patched {file_path}")
