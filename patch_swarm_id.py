import re

def patch_file(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Find the class definition line
    class_line_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('class LegislativeMonitorAgent(BaseAgent):'):
            class_line_idx = i
            break

    if class_line_idx == -1:
        print("Could not find class LegislativeMonitorAgent")
        return False

    # Insert class variables after the class definition line
    # We'll insert after the line that has the class definition and the docstring (if any)
    # Look for the line after the class definition that is not empty and not a comment? 
    # Instead, we'll insert right after the class definition line, but before the docstring if it exists on the next line.
    # Let's find the first non-empty line after the class definition that is not part of the docstring.
    # For simplicity, we'll insert after the class definition line and before the docstring if it starts with triple quotes.
    insert_at = class_line_idx + 1
    # If the next line starts with triple quotes, we want to insert after the docstring.
    if insert_at < len(lines) and lines[insert_at].strip().startswith('"""'):
        # Find the end of the docstring
        j = insert_at + 1
        while j < len(lines) and not lines[j].strip().endswith('"""'):
            j += 1
        if j < len(lines):
            insert_at = j + 1  # after the closing triple quotes
        else:
            insert_at = class_line_idx + 1  # fallback
    else:
        insert_at = class_line_idx + 1

    # Insert the class variables
    lines.insert(insert_at, '    SWARM_ID = "affirm_policy_swarm"\n')
    lines.insert(insert_at + 1, '    PROJECT_SCOPE = "affirm_bnpl_policy"\n')

    # Now, we need to modify the __init__ method to set instance variables if needed.
    # We'll just use the class variables directly in the methods, so no change to __init__ is strictly necessary.
    # But for clarity, we can set them in __init__ as well.
    # Find the __init__ method
    init_start = -1
    for i in range(len(lines)):
        if lines[i].strip().startswith('def __init__(self, agent_id: str = None, role: str = "Legislative Monitor Agent"):'):
            init_start = i
            break

    if init_start != -1:
        # Find the end of the __init__ method (look for the next method definition or end of class)
        # We'll look for the line that has the same indentation as the def __init__ and is not inside the method.
        # For simplicity, we'll just insert after the line that sets self.last_heartbeat and self.start_time
        # We know the __init__ method sets:
        # self.agent_id = agent_id or f"{role.lower()}-{str(uuid.uuid4())[:8]}"
        # self.role = role
        # ... then later ...
        # self.last_hearbeat = time.time()
        # self.start_time = time.time()
        # We'll insert after self.start_time = time.time()
        for i in range(init_start, len(lines)):
            if 'self.start_time = time.time()' in lines[i]:
                # Insert after this line
                lines.insert(i+1, '        self.SWARM_ID = self.__class__.SWARM_ID\n')
                lines.insert(i+2, '        self.PROJECT_SCOPE = self.__class__.PROJECT_SCOPE\n')
                break

    # Now, we need to modify the _store_legislative_results method.
    # We'll find the method and then replace the relevant parts.

    # First, find the method definition
    store_method_start = -1
    for i in range(len(lines)):
        if lines[i].strip().startswith('def _store_legislative_results(self, analyzed_items: List[Dict[str, Any]], jurisdiction: str, product: str) -> Optional[str]:'):
            store_method_start = i
            break

    if store_method_start != -1:
        # We'll now look for the two session.run calls and the MATCH in the verification method later.
        # We'll do the replacements by scanning the lines and modifying the specific lines.

        # We'll change the LegislativeMonitorRun CREATE query string.
        # Look for the line that has: 'CREATE (r:LegislativeMonitorRun {'
        for i in range(store_method_start, len(lines)):
            if 'CREATE (r:LegislativeMonitorRun {' in lines[i]:
                # We want to add swarm_id and project_scope to the properties.
                # The line currently looks like:
                #                 CREATE (r:LegislativeMonitorRun {
                #                     id: $run_id,
                #                     timestamp: $timestamp,
                #                     jurisdiction: $jurisdiction,
                #                     product: $product,
                #                     items_count: $items_count,
                #                     relevant_count: $relevant_count
                #                 })
                # We'll change it to:
                #                 CREATE (r:LegislativeMonitorRun {
                #                     id: $run_id,
                #                     timestamp: $timestamp,
                #                     jurisdiction: $jurisdiction,
                #                     product: $product,
                #                     items_count: $items_count,
                #                     relevant_count: $relevant_count,
                #                     swarm_id: $swarm_id,
                #                     project_scope: $project_scope
                #                 })
                # We'll do this by inserting two lines before the closing brace.
                # Find the line with the closing brace for this block.
                j = i
                while j < len(lines) and '                })' not in lines[j]:
                    j += 1
                if j < len(lines):
                    # Insert before the line that has '                })'
                    lines.insert(j, '                    swarm_id: $swarm_id,\n')
                    lines.insert(j+1, '                    project_scope: $project_scope,\n')
                break

        # Now, we need to add the parameters to the session.run call for this query.
        # Look for the line that has: '                result = session.run(query, {'
        for i in range(store_method_start, len(lines)):
            if 'result = session.run(query, {' in lines[i] and 'LegislativeMonitorRun' in ''.join(lines[max(0,i-10):i+10]):
                # We'll add the parameters inside the dictionary.
                # Find the line with the closing brace of the dictionary.
                j = i
                while j < len(lines) and '})' not in lines[j]:
                    j += 1
                if j < len(lines):
                    # Insert before the line that has '                })'
                    lines.insert(j, '                    "swarm_id": self.SWARM_ID,\n')
                    lines.insert(j+1, '                    "project_scope": self.PROJECT_SCOPE,\n')
                break

        # Now, the LegislativeItem CREATE query string.
        for i in range(store_method_start, len(lines)):
            if 'CREATE (i:LegislativeItem {' in lines[i]:
                # We'll add swarm_id to the properties.
                # Find the line with the closing brace for this block.
                j = i
                while j < len(lines) and '                    })' not in lines[j]:
                    j += 1
                if j < len(lines):
                    lines.insert(j, '                    swarm_id: $swarm_id,\n')
                break

        # Now, the parameters for the LegislativeItem session.run call.
        for i in range(store_method_start, len(lines)):
            if 'session.run(item_query, {' in lines[i]:
                # We'll add the swarm_id parameter.
                # Find the line with the closing brace of the dictionary.
                j = i
                while j < len(lines) and '                })' not in lines[j]:
                    j += 1
                if j < len(lines):
                    lines.insert(j, '                        "swarm_id": self.SWARM_ID,\n')
                break

    # Now, we need to modify the _verify_legislative_storage method.
    verify_method_start = -1
    for i in range(len(lines)):
        if lines[i].strip().startswith('def _verify_legislative_storage(self, run_id: str) -> bool:'):
            verify_method_start = i
            break

    if verify_method_start != -1:
        # Change the MATCH line to include swarm_id.
        for i in range(verify_method_start, len(lines)):
            if 'MATCH (r:LegislativeMonitorRun {id: $run_id})' in lines[i]:
                lines[i] = lines[i].replace('MATCH (r:LegislativeMonitorRun {id: $run_id})', 
                                           'MATCH (r:LegislativeMonitorRun {id: $run_id, swarm_id: $swarm_id})')
                break

        # Now, add the swarm_id parameter to the session.run call in this method.
        for i in range(verify_method_start, len(lines)):
            if 'result = session.run(query, {"run_id": run_id})' in lines[i]:
                lines[i] = lines[i].replace('result = session.run(query, {"run_id": run_id})', 
                                           'result = session.run(query, {"run_id": run_id, "swarm_id": self.SWARM_ID})')
                break

    # Write the file back
    with open(file_path, 'w') as f:
        f.writelines(lines)

    return True

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python patch_swarm_id.py <file_path>")
        sys.exit(1)
    file_path = sys.argv[1]
    if patch_file(file_path):
        print(f"Patched {file_path}")
    else:
        print(f"Failed to patch {file_path}")
        sys.exit(1)
