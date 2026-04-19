from core.world import World
from core.enums import EntityType
w = World()
w.entities = w.entities[:30]
for _ in range(601):
    w.step()
all_bugs = [e for e in w.entities if e.entity_type == EntityType.BUG]
dead = [b for b in all_bugs if not b.alive]
print(f"all_bugs={len(all_bugs)} dead={len(dead)}")
for b in all_bugs:
    print(f"  bug#{b.id} alive={b.alive} found={b.found_bug_in} reported_to={b.reported_to_dev}")
print(f"\ntotal_bug_reports={w.total_bug_reports}")
fixers = [e for e in w.entities if e.bugs_fixed > 0]
for f in fixers:
    print(f"  dev#{f.id} fixed {f.bugs_fixed}")
