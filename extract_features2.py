import re

with open(r'd:\world3\dashboard\dist\assets\index-BKymbBSF.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the editor tab content
print("=== EDITOR TAB ===")
for m in re.finditer(r'l==="editor"&&', content):
    section = content[m.start():m.start()+3000]
    print(section[:3000])
    print("\n")

# Find settlement/project phases
print("\n=== PROJECT PHASES ===")
phases = re.findall(r'"(architecture|development|review|push|testing|planning|design|deployment)"', content)
print("Phases:", sorted(set(phases)))

# Find all useCallback/useState/useEffect patterns for state variables
print("\n=== STATE & HOOKS ===")
# Look for useState initial states
states = re.findall(r'C\.useState\(([^)]{0,50})\)', content)
print("useState calls:", len(states))
for s in states[:30]:
    print(f"  useState({s})")

# Find interval/polling patterns
print("\n=== POLLING/TIMERS ===")
timeouts = re.findall(r'setTimeout\([^,]+,\s*(\d+)\)', content)
print("setTimeout values:", timeouts[:20])

# useEffect with intervals
effects = re.findall(r'(\d{3,5})\)', content)  # Large numbers that could be intervals

# Find population chart data structure
print("\n=== POPULATION CHART DATA ===")
for key in ['developer', 'bug', 'refactorer', 'senior', 'intern', 'copilot']:
    count = content.count(f'dataKey:"{key}"')
    print(f"  dataKey '{key}': {count} occurrences")

# Find completed projects section
print("\n=== COMPLETED PROJECTS SECTION ===")
idx = content.find('completed-projects')
if idx >= 0:
    print(content[idx-200:idx+200])

# Find project queue section
print("\n=== PROJECT QUEUE ===")
idx = content.find('project/queue')
if idx >= 0:
    print(content[idx-100:idx+300])

# Find GitHub push/integration features
print("\n=== GITHUB FEATURES ===")
github_patterns = ['github_url', 'github/status', 'github/configure', 'github/disconnect', 'projects_pushed', 'total_files_pushed', 'queue_size']
for p in github_patterns:
    if p in content:
        idx = content.find(p)
        print(f"{p}: ...{content[max(0,idx-50):idx+100]}...")

# Find the CSS file content
print("\n=== CSS FILE ===")
with open(r'd:\world3\dashboard\dist\assets\index-NG5dVJqw.css', 'r', encoding='utf-8') as f:
    css = f.read()
print(css[:6000])
