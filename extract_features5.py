import re

with open(r'd:\world3\dashboard\dist\assets\index-BKymbBSF.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the code snippet card properties (in the code tab)
print("=== CODE TAB SNIPPET PROPERTIES ===")
for m in re.finditer(r'snippet-card', content):
    section = content[m.start()-100:m.start()+600]
    print(section[:700])
    print()
    break

# Find the project queue features
print("\n=== PROJECT QUEUE RENDERING ===")
for m in re.finditer(r'Queue \(', content):
    section = content[m.start()-200:m.start()+400]
    print(section[:600])
    print()

# Find all tech stack options
print("\n=== TECH STACK OPTIONS ===")
tech = re.findall(r'"(Python|JavaScript|Rust|Go|HTML/CSS|SQL|TypeScript|Java|C\+\+|Ruby)"', content)
print("Tech stacks:", sorted(set(tech)))

# Find max_files range slider
print("\n=== FILES SLIDER ===")
idx = content.find('type:"range"')
if idx >= 0:
    section = content[idx-200:idx+200]
    print(section)

# Find the reset handler - what gets cleared
print("\n=== RESET HANDLER ===")
idx = content.find('Reset world')
if idx >= 0:
    section = content[idx-100:idx+400]
    print(section)

# Find the "Ready for push" feature
print("\n=== PUSH STATUS ===")
idx = content.find('Ready for push')
if idx >= 0:
    section = content[idx-300:idx+200]
    print(section)

# Find progress bar features
print("\n=== PROJECT PROGRESS ===")
idx = content.find('progress/100')
if idx >= 0:
    section = content[idx-200:idx+200]
    print(section)

# Find active project review_rounds, team_meetings
print("\n=== ACTIVE PROJECT DETAIL ===")
for m in re.finditer(r'review_rounds', content):
    section = content[m.start()-200:m.start()+200]
    print(section[:400])
    print()

# Check for the connection status indicator  
print("\n=== CONNECTION STATUS ===")
for m in re.finditer(r'connected|disconnected', content[570000:]):
    idx = m.start() + 570000
    section = content[idx-50:idx+100]
    if 'style' in section or 'children' in section:
        print(section)
        print()

# Find API base URL handling
print("\n=== API BASE URL ===")
idx = content.find('je=')
if idx >= 0:
    section = content[max(0,idx-50):idx+200]
    print(section)
else:
    # look for je definition
    for m in re.finditer(r'const je=', content):
        section = content[m.start():m.start()+200]
        print(section)
        break

# Find complete projects section
print("\n=== COMPLETED PROJECTS RENDERING ===")
idx = content.find('Completed projects')
if idx >= 0:
    section = content[idx-100:idx+800]
    print(section[:900])
