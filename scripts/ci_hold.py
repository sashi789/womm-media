#!/usr/bin/env python3
"""Hold or release a queued post. Usage: ci_hold.py hold|release [YYYY-MM-DD]"""
import sys

from ci_common import load_schedule, save_schedule, today

action = sys.argv[1]
day = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else today()
src, dst = ("queued", "held") if action == "hold" else ("held", "queued")
s, changed = load_schedule(), []
for p in s["posts"]:
    if p["date"] == day and p["status"] == src:
        p["status"] = dst
        changed.append(p["name"])
save_schedule(s)
print(f"{action} {day}: {changed or 'nothing matched'}")
