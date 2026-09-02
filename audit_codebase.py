import os, re

workspace_dir = os.path.expanduser("~/.openclaw/workspace/affirm_policy_swarm")

keywords = [
    r"\bmock\b",
    r"\bsimulat\w*",
    r"\bdummy\b",
    r"text_excerpt\s*=\s*[\"']",
    r"text_context\s*=\s*[\"']",
    r"q\s*=\s*[\"'][^\"']{10,}",
    r"query\s*=\s*[\"'][^\"']{10,}",
    r"fallback_records\.append",
    r"records\.append\(\s*\{\s*[\"']source[\"']"
]

print("🔍 ========================================================")
print(f"   SCANNING CODEBASE AT: {workspace_dir}")
print("========================================================\n")

flagged_count = 0

for root, _, files in os.walk(workspace_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, workspace_dir)
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            file_flags = []
            for idx, line in enumerate(lines, 1):
                # Skip pure comment lines or logger statements
                stripped = line.strip()
                if stripped.startswith("#") or "logger.info" in line or "print(" in line:
                    continue
                    
                for kw in keywords:
                    if re.search(kw, line, re.IGNORECASE):
                        file_flags.append((idx, line.strip()))
                        break
                        
            if file_flags:
                flagged_count += len(file_flags)
                print(f"📄 File: {rel_path}")
                for line_num, code_snippet in file_flags:
                    print(f"   Line {line_num:3d}: {code_snippet}")
                print("-" * 60)

if flagged_count == 0:
    print("✨ Clean audit! No hardcoding, mock strings, or static fallbacks found.")
else:
    print(f"\n⚠️ Audit completed: Found {flagged_count} potentially hardcoded or mock lines across the project.")

