import traceback
try:
    from core.world import World
    from core.enums import EntityType
    w = World()
    w.entities = w.entities[:30]
    for i in range(601):
        try:
            w.step()
        except Exception as ex:
            print(f"ERROR at tick {w.tick}: {ex}")
            traceback.print_exc()
            break
        if w.tick % 100 == 0:
            alive = [e for e in w.entities if e.alive]
            print(f"tick={w.tick} alive={len(alive)} code={w.total_code_generated} "
                  f"reports={w.total_bug_reports} sett={len(w.settlements)}")

    all_bugs = [e for e in w.entities if e.entity_type == EntityType.BUG]
    dead_bugs_reported = [b for b in all_bugs if not b.alive and b.reported_to_dev is not None]
    found = [b for b in all_bugs if b.found_bug_in is not None]
    fixers = [e for e in w.entities if e.bugs_fixed > 0]
    buggy = [s for s in w.code_snippets.values() if s.has_bugs]
    print(f"\nFINAL: tick={w.tick} total_bugs={len(all_bugs)} found={len(found)} "
          f"reported={len(dead_bugs_reported)} reports={w.total_bug_reports}")
    print(f"fixers={len(fixers)} buggy_left={len(buggy)} snippets={len(w.code_snippets)}")
    for b in dead_bugs_reported[:5]:
        print(f"  Bug #{b.id} -> Dev #{b.reported_to_dev}, snippet #{b.found_bug_in}")
    for f in fixers[:5]:
        print(f"  Dev #{f.id} fixed {f.bugs_fixed} bugs")
except Exception as ex:
    print(f"FATAL: {ex}")
    traceback.print_exc()
