#!/usr/bin/env python3
"""Post today's queued Reel. Posts at most one video, never the same video twice."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
import time
import urllib.request

from ci_common import CFG, GRAPH, LOG, QUEUE, ROOT, SUFFIX, call, load_schedule, save_schedule, slot, today, token

def within_window(when, now):
    """GitHub's own scheduler can fire hours late; only post inside the slot's real window (local time)."""
    mins = now.hour * 60 + now.minute
    lo, hi = (9 * 60, 14 * 60) if when == "am" else (21 * 60 + 30, 24 * 60)
    return lo <= mins < hi


DRY = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")


def main():
    day, when = today(), slot()
    sched = load_schedule()
    if (ROOT / "HOLD").exists() or (SUFFIX and (ROOT / f"HOLD{SUFFIX}").exists()):
        print("A HOLD file is present: posting is paused.")
        return
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and not DRY:
        now = datetime.now(ZoneInfo(CFG["timezone"]))
        if not within_window(when, now):
            print(f"Scheduled run at {now:%H:%M} local is outside the {when} window (am 09:00 to 14:00, pm 21:30 to midnight); not posting.")
            return
    entry = next((p for p in sched["posts"] if p["date"] == day and p.get("slot", "pm") == when
                  and p["status"] == "queued"), None)
    if entry is None:
        states = [f"{p['name']}({p.get('slot', 'pm')})={p['status']}" for p in sched["posts"] if p["date"] == day]
        print(f"Nothing to post for {day} {when}. Entries for today: {states or 'none'}")
        return
    name = entry["name"]
    log = LOG
    done = [l.split() for l in log.read_text().splitlines()] if log.exists() else []
    if any(len(p) > 2 and p[2] == name for p in done):
        entry["status"] = "posted"
        save_schedule(sched)
        print(f"{name} is already in published.log; not posting again.")
        return

    video, cap = QUEUE / f"{name}.mp4", QUEUE / f"{name}.txt"
    if not video.exists() or not cap.exists():
        raise RuntimeError(f"{QUEUE.name}/{name}.mp4 or {QUEUE.name}/{name}.txt is missing")
    text, meta = cap.read_text(), {}
    if "\n---\n" in text:
        head, text = text.split("\n---\n", 1)
        meta = {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in head.splitlines() if ":" in l)}
    caption = text.strip()
    url = f"{CFG['base_url']}/{QUEUE.name}/{name}.mp4"
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as r:
        if int(r.headers.get("Content-Length", 0)) != video.stat().st_size:
            raise RuntimeError(f"{url} is not serving the queued file yet")
    tok = token()
    me = call("GET", f"{GRAPH}/{CFG['ig_user_id']}", tok, {"fields": "username"})
    print(f"Account @{me.get('username')}; video {url}; caption {len(caption)} characters.")
    if DRY:
        print("Dry run: everything checks out, nothing was posted.")
        return

    params = {"media_type": "REELS", "video_url": url, "caption": caption, "share_to_feed": "true"}
    if meta.get("thumb_seconds"):
        params["thumb_offset"] = str(int(float(meta["thumb_seconds"]) * 1000))
    cid = call("POST", f"{GRAPH}/{CFG['ig_user_id']}/media", tok, params)["id"]
    for _ in range(120):
        st = call("GET", f"{GRAPH}/{cid}", tok, {"fields": "status_code,status"})
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram could not process the video: {st}")
        time.sleep(5)
    else:
        raise RuntimeError("Timed out waiting for Instagram to process the video")
    post = call("POST", f"{GRAPH}/{CFG['ig_user_id']}/media_publish", tok, {"creation_id": cid})
    link = call("GET", f"{GRAPH}/{post['id']}", tok, {"fields": "permalink"}).get("permalink", "")
    entry.update(status="posted", link=link, media_id=post["id"])
    save_schedule(sched)
    with log.open("a") as f:
        f.write(f"{day} {time.strftime('%H:%M')}  {name}  {post['id']}  {link}\n")
    print(f"Posted {name}: {link}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # record the failure so the same video is not retried blindly
        try:
            s = load_schedule()
            for p in s["posts"]:
                if p["date"] == today() and p.get("slot", "pm") == slot() and p["status"] == "queued" and not DRY:
                    p.update(status="post_failed", error=str(e)[:300])
            save_schedule(s)
        finally:
            sys.exit(f"Posting failed: {e}")
