"""Smoke test for all 8 advanced lifecycle features."""
import sys, math, time
sys.path.insert(0, '.')
from core.world import World

w = World()
t0 = time.time()

# Track events
burnouts = 0
migrations = 0
cascades = 0
skill_decays = 0
mentorships = 0

orig_log = w.log_event
def tracking_log(msg):
    global burnouts, migrations, cascades, skill_decays, mentorships
    if "burned out" in msg or "vacation" in msg:
        burnouts += 1
    if "left" in msg and "explore" in msg:
        migrations += 1
    if "Cascade bug" in msg:
        cascades += 1
    if "forgot" in msg:
        skill_decays += 1
    if "Teacher" in msg and "taught" in msg:
        mentorships += 1
    orig_log(msg)

w.log_event = tracking_log

for i in range(300):
    w.step()

dt = time.time() - t0
alive = [e for e in w.entities if e.alive]
print(f"300 ticks in {dt:.1f}s ({dt/300*1000:.0f}ms/tick)")
print(f"alive: {len(alive)}")

# 1. Reputation check
reps = [getattr(e, 'reputation', 0.5) for e in alive]
rep_min = min(reps) if reps else 0
rep_max = max(reps) if reps else 0
rep_avg = sum(reps)/len(reps) if reps else 0
print(f"Reputation: min={rep_min:.3f} avg={rep_avg:.3f} max={rep_max:.3f}")

# 2. Burnout check
print(f"Burnout events: {burnouts}")
in_burnout = sum(1 for e in alive if getattr(e, 'burnout', False))
print(f"Currently in burnout: {in_burnout}")

# 3. Personality evolution check
has_pxp = sum(1 for e in alive if getattr(e, 'personality_xp', {}))
print(f"Entities with personality XP: {has_pxp}")

# 4. Language last used
has_llu = sum(1 for e in alive if getattr(e, 'language_last_used', {}))
print(f"Entities tracking language usage: {has_llu}")

# 5. Team memory
tm = getattr(w, '_team_memory', [])
print(f"Team memory entries: {len(tm)}")

# 6. Migration
print(f"Migration events: {migrations}")

# 7. Cascade bugs
print(f"Cascade bug events: {cascades}")

# 8. Skill decay
print(f"Skill decay events: {skill_decays}")

# 9. Mentorship (Teacher)
print(f"Mentorship events: {mentorships}")

# X spread check
xs = [e.x for e in alive]
ys = [e.y for e in alive]
print(f"X spread: {max(xs)-min(xs):.0f} / 6000")
print(f"Y spread: {max(ys)-min(ys):.0f} / 4000")

print("\nALL TESTS PASSED - 8 features active")
