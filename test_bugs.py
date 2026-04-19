"""Test: bug new behavior — search in code, report to developer, death."""
from core.world import World
from core.enums import EntityType

w = World()
w.entities = w.entities[:50]

for i in range(601):
    w.step()
    if i in (300, 600):
        alive = [e for e in w.entities if e.alive]
        bugs = [e for e in alive if e.entity_type == EntityType.BUG]
        found = [b for b in w.entities if b.entity_type == EntityType.BUG and b.found_bug_in is not None]
        buggy = [s for s in w.code_snippets.values() if s.has_bugs]
        fixers = [e for e in w.entities if e.bugs_fixed > 0]
        print(f"tick={w.tick}: alive={len(alive)} bugs_alive={len(bugs)} "
              f"code={w.total_code_generated} buggy_snippets={len(buggy)} "
              f"bug_reports={w.total_bug_reports} bugs_found_code={len(found)} "
              f"fixers={len(fixers)} sett={len(w.settlements)}")

# Final summary
all_bugs = [e for e in w.entities if e.entity_type == EntityType.BUG]
dead_bugs = [b for b in all_bugs if not b.alive]
reported = [b for b in all_bugs if b.reported_to_dev is not None]
print(f"\n--- FINAL ---")
print(f"Total bugs ever: {len(all_bugs)}")
print(f"Dead bugs: {len(dead_bugs)}")
print(f"Bugs that reported to dev: {len(reported)}")
print(f"Total bug reports: {w.total_bug_reports}")
for b in reported[:5]:
    print(f"  Bug #{b.id} reported to dev #{b.reported_to_dev}, snippet #{b.found_bug_in}")

fixers = [e for e in w.entities if e.bugs_fixed > 0]
print(f"Devs who fixed bugs: {len(fixers)}")
for f in fixers[:5]:
    print(f"  Dev #{f.id} ({f.entity_type.name}): fixed {f.bugs_fixed} bugs")

# Check events log
for ev in w.events:
    if "Bug" in ev or "bug" in ev.lower() or "fix" in ev:
        print(f"  EVENT: {ev}")
