import os, sys, importlib

print("\n========================================")
print(" OPENCLAW COMPREHENSIVE SWARM AUDIT")
print("========================================\n")

print("[*] Phase 1: Module Compilation & Import Verification")
agents_dir = "agents"
sys.path.append(os.path.abspath("."))
success_count = 0
failed_modules = []

for file in sorted(os.listdir(agents_dir)):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = f"agents.{file[:-3]}"
        try:
            importlib.import_module(module_name)
            print(f"  [+] {file} compiled successfully")
            success_count += 1
        except Exception as e:
            print(f"  [-] {file} FAILED: {e}")
            failed_modules.append(file)

print(f"\n[*] Phase 1 Complete: {success_count} modules healthy.")
if failed_modules:
    print(f"[*] WARNING: {len(failed_modules)} modules failed to load.")

print("\n[*] Phase 2: JSON Parsing Vulnerability Check")
files_to_check = ["entity_resolution_agent.py", "risk_scoring_agent.py"]
for f in files_to_check:
    path = os.path.join(agents_dir, f)
    if os.path.exists(path):
        with open(path, "r") as file:
            content = file.read()
            if "```json" in content or "replace('```json'" in content or "strip()" in content:
                print(f"  [-] {f} is vulnerable: Missing strict regex extraction for JSON blocks.")
            else:
                print(f"  [-] {f} is highly vulnerable: No markdown stripping logic detected.")

print("\n========================================\n")
