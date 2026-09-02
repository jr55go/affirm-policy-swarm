path = 'agents/reporting_agent.py'
with open(path, 'r') as f:
    content = f.read()

target = "os.makedirs(report_dir, exist_ok=True)"
replacement = """os.makedirs(report_dir, exist_ok=True)
        try:
            manager = get_db_manager()
            if hasattr(manager, "initialize"): manager.initialize()
            elif hasattr(manager, "connect"): manager.connect()
        except:
            pass"""

if "manager.initialize()" not in content:
    content = content.replace(target, replacement)
    with open(path, 'w') as f:
        f.write(content)
    print("Patched ReportingAgent to initialize Neo4j.")
