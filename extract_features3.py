import re

with open(r'd:\world3\dashboard\dist\assets\index-BKymbBSF.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the polling setup (setInterval calls)
print("=== POLLING INTERVALS ===")
for m in re.finditer(r'setInterval\(', content):
    section = content[m.start():m.start()+200]
    print(section[:200])
    print()

# Find the data fetching callbacks
print("\n=== CALLBACK FUNCTIONS ===")
for m in re.finditer(r'useCallback\(async', content):
    section = content[m.start():m.start()+300]
    print(section[:300])
    print()

# Find the world_tick socket handler
print("\n=== WORLD_TICK HANDLER ===")
idx = content.find('world_tick')
section = content[idx-100:idx+500]
print(section)

# Find "events" socket handler
print("\n=== EVENTS HANDLER ===")
for m in re.finditer(r'\.on\("events"', content):
    section = content[m.start():m.start()+500]
    print(section[:500])
    print()

# Find all properties of entity data
print("\n=== ENTITY PROPERTIES ===")
entity_props = re.findall(r'a\.([\w]+)', content[589000:593000])
print("Entity detail properties:", sorted(set(entity_props)))

# Find project active properties
print("\n=== ACTIVE PROJECT PROPERTIES ===")
proj_props = re.findall(r'active_project\.([\w]+)', content)
print("Active project properties:", sorted(set(proj_props)))

# Find status response properties
print("\n=== STATUS RESPONSE PROPERTIES ===")
for m in re.finditer(r'G\.([\w]+)', content[612000:615000]):
    pass
status_props = re.findall(r'G\.([\w]+)', content[585000:615000])
print("Status properties:", sorted(set(status_props)))

# Settlement properties
print("\n=== SETTLEMENT PROPERTIES ===")
sett_props = re.findall(r'Y\.([\w]+)', content[576000:586000])
print("Settlement entity props:", sorted(set(sett_props)))

# Find typing animation / streaming effect
print("\n=== TYPING/STREAMING EFFECT ===")
idx = content.find('blink')
if idx >= 0:
    print(content[idx-100:idx+200])

# Find the code snippets / snippet-card properties
print("\n=== CODE SNIPPET PROPERTIES ===")
snippet_props = re.findall(r'j\.([\w]+)', content[596000:598000])
print("Snippet card props:", sorted(set(snippet_props)))

# Find all h4 section headers
print("\n=== ALL H4 SECTION HEADERS ===")
headers = re.findall(r'h4.*?children:"([^"]+)"', content)
print("Section headers:", sorted(set(headers)))
