import re

def patch_legislative_monitor(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # 1. Add class variables after the class definition
    # Find the line with the class definition
    class_pattern = r'(class LegislativeMonitorAgent\(BaseAgent\):)'
    # We'll insert after this line
    replacement = r'\1\n    SWARM_ID = "affirm_policy_swarm"\n    PROJECT_SCOPE = "affirm_bnpl_policy"'
    content = re.sub(class_pattern, replacement, content)

    # 2. Add instance variables in __init__
    # Find the __init__ method and insert after the line that sets self.start_time
    init_pattern = r'(def __init__\(self, agent_id: str = None, role: str = "Legislative Monitor Agent"\):[\s\S]*?self\.start_time = time\.time\(\))'
    # We'll use a function to add the lines after the match
    def add_ivars(match):
        return match.group(1) + '\n        self.SWARM_ID = self.__class__.SWARM_ID\n        self.PROJECT_SCOPE = self.__class__.PROJECT_SCOPE'
    content = re.sub(init_pattern, add_ivars, content, flags=re.DOTALL)

    # 3. Update the LegislativeMonitorRun CREATE in _store_legislative_results
    # We'll find the CREATE line and add two properties before the closing brace.
    # We'll use a regex to capture the CREATE block and then modify it.
    # We'll look for: CREATE (r:LegislativeMonitorRun { ... })
    # We want to insert two lines before the closing brace.
    # We'll do it by replacing the closing brace line with our two lines and then the brace.
    # We'll do a more precise replacement: we'll look for the line that has the closing brace of the CREATE statement.
    # We'll replace that line with:
    #                     swarm_id: $swarm_id,
    #                     project_scope: $project_scope
    #                 })
    # But note: the indentation might be 20 spaces (5 tabs? but we use spaces). We'll keep the same indentation as the line before.
    # Instead, we'll do a string replacement for the specific block we know.
    # We know the block looks like:
    #                 CREATE (r:LegislativeMonitorRun {
    #                     id: $run_id,
    #                     timestamp: $timestamp,
    #                     jurisdiction: $jurisdiction,
    #                     product: $product,
    #                     items_count: $items_count,
    #                     relevant_count: $relevant_count
    #                 })
    # We want to change it to:
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
    # We'll do a regex that matches from the line with 'CREATE (r:LegislativeMonitorRun {' to the line with '                })'
    # and then insert the two lines before the last line.
    # We'll use a regex with groups: (the opening lines) and (the closing line) and then replace.
    # We'll break the content into lines and process line by line for this part to avoid complex regex.
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('CREATE (r:LegislativeMonitorRun {'):
            # We found the start of the block.
            # We'll add this line and then the next lines until we find the line that has '                })'
            # We'll collect the block lines.
            block_lines = [line]
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('})'):
                block_lines.append(lines[j])
                j += 1
            if j < len(lines):
                block_lines.append(lines[j])  # the line with '                })'
                # Now we have the block from i to j (inclusive)
                # We want to insert two lines before the last line.
                # The last line is block_lines[-1]
                # We'll insert two lines with the same indentation as the first line in the block (after the opening brace).
                # The first line in the block is the CREATE is block_lines is the 'CREATE (r:LegislativeMonitorRun {' line.
                # The second line is the first property.
                # We'll use the indentation of the second line.
                if len(block_lines) >= 2:
                    indent = len(block_lines[1]) - len(block_lines[1].lstrip())
                    line1 = ' ' * indent + 'swarm_id: $swarm_id,'
                    line2 = ' ' * indent + 'project_scope: $project_scope'
                    # Insert these two lines before the last line
                    new_lines.extend(block_lines[:-1])
                    new_lines.append(line1)
                    new_lines.append(line2)
                    new_lines.append(block_lines[-1])
                else:
                    # If there are no properties, we just add the two lines before the closing brace.
                    new_lines.extend(block_lines[:-1])
                    new_lines.append(' ' * (len(block_lines[0]) - len(block_lines[0].lstrip())) + 'swarm_id: $swarm_id,')
                    new_lines.append(' ' * (len(block_lines[0]) - len(block_lines[0].lstrip())) + 'project_scope: $project_scope')
                    new_lines.append(block_lines[-1])
                i = j + 1
                continue
        new_lines.append(line)
        i += 1
    content = '\n'.join(new_lines)

    # 4. Update the LegislativeItem CREATE (r:LegislativeMonitorRun {'
    # We'll do a simpler approach: we'll just replace the known string with the new one.
    # Since we know the exact original string (with the exact indentation) from the file, we can do a string replace.
    # But note: the indentation might be exactly 20 spaces (5 tabs? but we use 4 spaces per indent, so 5*4=20).
    # We'll do:
    old_block = '''                CREATE (r:LegislativeMonitorRun {
                    id: $run_id,
                    timestamp: $timestamp,
                    jurisdiction: $jurisdiction,
                    product: $product,
                    items_count: $items_count,
                    relevant_count: $relevant_count
                })'''
    new_block = '''                CREATE (r:LegislativeMonitorRun {
                    id: $run_id,
                    timestamp: $timestamp,
                    jurisdiction: $jurisdiction,
                    product: $product,
                    items_count: $items_count,
                    relevant_count: $relevant_count,
                    swarm_id: $swarm_id,
                    project_scope: $project_scope
                })'''
    content = content.replace(old_block, new_block)

    # 5. Update the LegislativeItem CREATE in the same method (inside the for loop)
    # We'll do similarly for the LegislativeItem block.
    old_block2 = '''                    CREATE (i:LegislativeItem {
                        id: $item_id,
                        title: $title,
                        sponsor: $sponsor,
                        introduced_date: $introduced_date,
                        latest_action: $latest_action,
                        url: $url,
                        keywords: $keywords,
                        relevance_score: $relevance_score,
                        potential_impact: $potential_impact
                    })'''
    new_block2 = '''                    CREATE (i:LegislativeItem {
                        id: $item_id,
                        title: $title,
                        sponsor: $sponsor,
                        introduced_date: $introduced_date,
                        latest_action: $latest_action,
                        url: $url,
                        keywords: $keywords,
                        relevance_score: $relevance_score,
                        potential_impact: $potential_impact,
                        swarm_id: $swarm_id
                    })'''
    content = content.replace(old_block2, new_block2)

    # 6. Update the session.run call for the LegislativeMonitorRun CREATE
    # We'll look for the line that has: result = session.run(query, {
    # and then we'll add the two parameters inside the dictionary.
    # We know the dictionary has:
    #                     "run_id": run_id,
    #                     "timestamp": timestamp,
    #                     "jurisdiction": jurisdiction,
    #                     "product": product,
    #                     "items_count": len(legislative_items),  # total fetched
    #                     "relevant_count": len([i for i in analyzed_items if i.get("potential_impact") in ["high", "medium"]])
    #                 })
    # We'll add two lines before the closing brace.
    old_run_call = '''                result = session.run(query, {
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "jurisdiction": jurisdiction,
                    "product": product,
                    "items_count": len(legislative_items),  # total fetched
                    "relevant_count": len([i for i in analyzed_items if i.get("potential_impact") in ["high", "medium"]])
                })'''
    new_run_call = '''                result = session.run(query, {
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "jurisdiction": jurisdiction,
                    "product": product,
                    "items_count": len(legislative_items),  # total fetched
                    "relevant_count": len([i for i in analyzed_items if i.get("potential_impact") in ["high", "medium"]]),
                    "swarm_id": self.SWARM_ID,
                    "project_scope": self.PROJECT_SCOPE
                })'''
    content = content.replace(old_run_call, new_run_call)

    # 7. Update the session.run call for the LegislativeItem CREATE inside the for loop
    # We'll look for the line that has: session.run(item_query, {
    # and then we'll add the two parameters.
    # We know the dictionary has:
    #                         "run_id": run_id,
    #                         "item_id": item.get("bill_id"),
    #                         "title": item.get("title"),
    #                         "sponsor": item.get("sponsor"),
    #                         "introduced_date": item.get("introduced_date"),
    #                         "latest_action": item.get("latest_action"),
    #                         "url": item.get("url"),
    #                         "keywords": item.get("keywords"),
    #                         "relevance_score": item.get("relevance_score"),
    #                         "potential_impact": item.get("potential_impact")
    #                     })
    # We'll add two lines before the closing brace.
    old_item_call = '''                    session.run(item_query, {
                        "run_id": run_id,
                        "item_id": item.get("bill_id"),
                        "title": item.get("title"),
                        "sponsor": item.get("sponsor"),
                        "introduced_date": item.get("introduced_date"),
                        "latest_action": item.get("latest_action"),
                        "url": item.get("url"),
                        "keywords": item.get("keywords"),
                        "relevance_score": item.get("relevance_score"),
                        "potential_impact": item.get("potential_impact")
                    })'''
    new_item_call = '''                    session.run(item_query, {
                        "run_id": run_id,
                        "item_id": item.get("bill_id"),
                        "title": item.get("title"),
                        "sponsor": item.get("sponsor"),
                        "introduced_date": item.get("introduced_date"),
                        "latest_action": item.get("latest_action"),
                        "url": item.get("url"),
                        "keywords": item.get("keywords"),
                        "relevance_score": item.get("relevance_score"),
                        "potential_impact": item.get("potential_impact"),
                        "swarm_id": self.SWARM_ID
                    })'''
    content = content.replace(old_item_call, new_item_call)

    # 8. Update the _verify_legislative_storage method
    # We'll change the MATCH line to include swarm_id.
    old_match = '                MATCH (r:LegislativeMonitorRun {id: $run_id})'
    new_match = '                MATCH (r:LegislativeMonitorRun {id: $run_id, swarm_id: $swarm_id})'
    content = content.replace(old_match, new_match)

    # And update the session.run call in that method to include the swarm_id parameter.
    old_verify_call = '                result = session.run(query, {"run_id": run_id})'
    new_verify_call = '                result = session.run(query, {"run_id": run_id, "swarm_id": self.SWARM_ID})'
    content = content.replace(old_verify_call, new_verify_call)

    with open(file_path, 'w') as f:
        f.write(content)

    print(f"Patched {file_path}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python patch_legislative.py <file_path>")
        sys.exit(1)
    patch_legislative_monitor(sys.argv[1])
