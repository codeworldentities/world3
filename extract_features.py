import re

with open(r'd:\world3\dashboard\dist\assets\index-BKymbBSF.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find socket.io event listeners (jn is the socket variable)
matches = re.findall(r'jn\.on\("([^"]+)"', content)
print('Socket.io events:', sorted(set(matches)))

# Find all .on("event_name" patterns
matches2 = re.findall(r'\.on\("([a-z_]+)"', content)
print('\nAll .on() events:', sorted(set(matches2)))

# Find EventSource / SSE
if 'EventSource' in content:
    print('\nHas EventSource/SSE')

# Find WebSocket
ws_count = content.count('WebSocket')
print(f'\nWebSocket refs: {ws_count}')

# Find socket.io transport info
idx = content.find('socket.io')
if idx >= 0:
    print(f'\nsocket.io context: ...{content[max(0,idx-100):idx+100]}...')

# Find all color constants (entity type colors)
print('\n--- Entity Types ---')
idx = content.find('Developer')
section = content[idx-200:idx+500]
print(section)

# Find the polling intervals / setInterval
intervals = re.findall(r'setInterval\([^,]+,\s*(\d+)\)', content)
print(f'\nsetInterval values (ms): {intervals}')

# Find useEffect dependencies that suggest polling
print('\n--- Instinct types ---')
instinct_matches = re.findall(r'Coding|Debug|Refactoring|Learn|Collaborate|Deploy', content)
print('Instincts found:', sorted(set(instinct_matches)))

# Find the error boundary
print('\n--- Error Boundary ---')
idx = content.find('getDerivedStateFromError')
if idx >= 0:
    print(content[idx-100:idx+500])

# Look for WebSocket events emitted or listened to
print('\n--- Socket events ---')
socket_events = re.findall(r'(?:emit|on)\("([^"]+)"', content)
print('All emit/on events:', sorted(set(socket_events)))

# Find editor tab - what does it show?
print('\n--- Editor Tab ---')
idx = content.find('"editor"')
if idx >= 0:
    # Find its rendering
    for m in re.finditer(r'l==="editor"', content):
        section = content[m.start()-100:m.start()+2000]
        print(section[:2000])
        break
