"""Shared helpers for the GitHub Actions jobs. Standard library only."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text())
GRAPH = f"https://graph.facebook.com/{CFG['api_version']}"
SCHEDULE = ROOT / "schedule.json"


def today():
    return os.environ.get("TODAY") or datetime.now(ZoneInfo(CFG["timezone"])).strftime("%Y-%m-%d")


def slot():
    """'am' for the morning run, 'pm' for the evening run (by local time unless SLOT is set)."""
    forced = os.environ.get("SLOT", "").strip().lower()
    if forced in ("am", "pm"):
        return forced
    return "am" if datetime.now(ZoneInfo(CFG["timezone"])).hour < 14 else "pm"


def token():
    tok = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not tok:
        sys.exit("The IG_ACCESS_TOKEN secret is not set for this repository.")
    return tok


def call(method, url, tok, params):
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Meta API error {e.code}: {e.read().decode(errors='replace')[:500]}")


def load_schedule():
    return json.loads(SCHEDULE.read_text())


def save_schedule(s):
    SCHEDULE.write_text(json.dumps(s, indent=2) + "\n")
