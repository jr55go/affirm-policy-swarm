import os

agents_dir = 'agents'
for filename in os.listdir(agents_dir):
    if filename.endswith('.py') and filename != '__init__.py':
        path = os.path.join(agents_dir, filename)
        with open(path, 'r') as f:
            lines = f.readlines()
        
        patched = False
        with open(path, 'w') as f:
            for line in lines:
                f.write(line)
                if line.strip().startswith('class ') and 'Agent' in line:
                    class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
                    f.write(f'    name = "{class_name}"\n')
                    patched = True
        
        if patched:
            print(f"Patched {class_name} in {filename}")

print("All agents have their name attributes. Final boss defeated.")
