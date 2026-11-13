#!/usr/bin/env python3
"""Collect numbers for every posted Reel into insights.json."""
import json
import time

from ci_common import GRAPH, ROOT, call, token

METRICS = "views,reach,saved,shares,total_interactions,ig_reels_avg_watch_time"
tok, rows, problem = token(), [], None
log = ROOT / "published.log"
for line in log.read_text().splitlines() if log.exists() else []:
    parts = line.split()
    if len(parts) < 4:
        continue
    row = {"date": parts[0], "name": parts[2], "media_id": parts[3]}
    try:
        b = call("GET", f"{GRAPH}/{parts[3]}", tok, {"fields": "like_count,comments_count,permalink"})
        row.update(likes=b.get("like_count"), comments=b.get("comments_count"), link=b.get("permalink"))
    except RuntimeError as e:
        row["error"] = str(e)[:200]
    try:
        for m in call("GET", f"{GRAPH}/{parts[3]}/insights", tok, {"metric": METRICS}).get("data", []):
            v = (m.get("values") or [{}])[0].get("value")
            if m["name"] == "ig_reels_avg_watch_time":
                row["avg_watch_seconds"] = round(v / 1000, 1) if v else v
            else:
                row[m["name"]] = v
    except RuntimeError as e:
        problem = str(e)[:200]
    rows.append(row)
out = {"pulled_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "insights_available": problem is None,
       "insights_error": problem, "reels": rows}
(ROOT / "insights.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
