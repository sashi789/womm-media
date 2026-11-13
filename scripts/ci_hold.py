#!/usr/bin/env python3
"""Hold or release queued posts. Usage: ci_hold.py hold|release [YYYY-MM-DD] [am|pm|both]"""
import sys

from ci_common import load_schedule, save_schedule, today

action = sys.argv[1]
day = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else today()
which = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else "both"
src, dst = ("queued", "held") if action == "hold" else ("held", "queued")
s, changed = load_schedule(), []
for p in s["posts"]:
    if p["date"] == day and p["status"] == src and which in ("both", p.get("slot", "pm")):
        p["status"] = dst
        changed.append(f"{p['name']} ({p.get('slot', 'pm')})")
save_schedule(s)
print(f"{action} {day} {which}: {changed or 'nothing matched'}")
