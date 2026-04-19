import re

with open(r'd:\world3\dashboard\dist\assets\index-BKymbBSF.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find population data structure in detail
print("=== POPULATION DATA STRUCTURE ===")
idx = content.find('developer||[])[Je]')
section = content[idx-200:idx+300]
print(section)

# Find auto-rotation of code snippets (editor tab)
print("\n=== CODE AUTO-ROTATION ===")
idx = content.find('Ye.current')
section = content[idx-200:idx+400]
print(section)

# Find the planned structure / file tree view
print("\n=== FILE TREE VIEW ===")
idx = content.find('Planned structure')
if idx >= 0:
    section = content[idx-200:idx+400]
    print(section)

# Find the snippet typing animation
print("\n=== TYPING ANIMATION ===")
idx = content.find('Math.random()*3)+1')
section = content[idx-300:idx+200]
print(section)

# Find project file structure
print("\n=== PROJECT FILE STRUCTURE ===")
idx = content.find('.tree')
if idx >= 0:
    section = content[idx-100:idx+300]
    print(section)

# Search for all CSS animations
print("\n=== CSS ANIMATIONS ===")
with open(r'd:\world3\dashboard\dist\assets\index-NG5dVJqw.css', 'r', encoding='utf-8') as f:
    css = f.read()
anims = re.findall(r'@keyframes\s+(\w+)', css)
print("Keyframe animations:", anims)

# Find all animation references in CSS
anim_refs = re.findall(r'animation:([^;}]+)', css)
print("\nAnimation usages:", anim_refs)

# Read rest of CSS
print("\n=== CSS (remaining) ===")
print(css[6000:])

# Find confirm dialogs
print("\n=== CONFIRM DIALOGS ===")
for m in re.finditer(r'confirm\("([^"]+)"', content):
    print(f"confirm: {m.group(1)}")

# Check for console.log/warn/info messages
print("\n=== CONSOLE MESSAGES ===")
for m in re.finditer(r'console\.(log|warn|info)\("([^"]+)"', content):
    print(f"console.{m.group(1)}: {m.group(2)}")

# Find soul properties
print("\n=== SOUL PROPERTIES ===")
idx = content.find('souls"')
# Find soul rendering section
for m in re.finditer(r'j\.persona', content):
    section = content[m.start()-500:m.start()+200]
    soul_props = re.findall(r'j\.([\w]+)', section)
    print("Soul properties:", sorted(set(soul_props)))
    break

# Find all class names used in the JS
print("\n=== ALL CLASSNAMES ===") 
classnames = re.findall(r'className:"([^"]+)"', content)
print("All classNames:", sorted(set(classnames)))
