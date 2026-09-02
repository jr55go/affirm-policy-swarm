import os
import re

connector_dir = "infrastructure/connectors/"
classes_defined = {}
imports_requested = []

# 1. Find all defined classes
for file in os.listdir(connector_dir):
    if file.endswith(".py") and not file.endswith(".bak"):
        filepath = os.path.join(connector_dir, file)
        try:
            with open(filepath, "r") as f:
                for line_num, line in enumerate(f, 1):
                    match = re.match(r"^class\s+([A-Za-z0-9_]+)", line)
                    if match:
                        classes_defined[match.group(1)] = file
        except: pass

# 2. Find all requested local imports
for file in os.listdir(connector_dir):
    if file.endswith(".py") and not file.endswith(".bak"):
        filepath = os.path.join(connector_dir, file)
        try:
            with open(filepath, "r") as f:
                for line_num, line in enumerate(f, 1):
                    if line.startswith("from ."):
                        imports_requested.append((file, line_num, line.strip()))
        except: pass

print("\n=== CLASSES DEFINED IN INFRASTRUCTURE/CONNECTORS/ ===")
for class_name, file in classes_defined.items():
    print(f"{class_name} (in {file})")

print("\n=== LOCAL IMPORTS REQUESTED ===")
for file, line, statement in imports_requested:
    print(f"File: {file} | Line {line} | Requested: {statement}")

print("\n")
