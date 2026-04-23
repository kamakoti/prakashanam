#!/usr/bin/env python3
"""
Find event pages dated for tomorrow (IST) and queue them as Google Calendar
events so that an existing IFTTT recipe ("Event starts" trigger on the dedicated
tweets calendar) can fire the tweet from @adyatithi.

IFTTT recipe wiring (already in place):
  - Description -> tweet body
  - Where (location) -> image URL

This script:
  1. Walks the repo for index.md files with YAML front matter
  2. Parses `date` from each
  3. For any event dated tomorrow AND not in tweeted.json:
       - Creates a calendar event starting ~5 minutes from now
         (gives IFTTT a moment to poll and pick it up)
       - Sets Description = composed tweet text
       - Sets Location  = cover.jpg URL (or "" if missing)
       - Records (folder@event_date) -> calendar event id in tweeted.json
  4. Commits the updated ledger back (handled by the workflow)

Env vars required:
  GOOGLE_SERVICE_ACCOUNT_JSON   JSON content of the service-account key
  CALENDAR_ID                   e.g. abc123@group.calendar.google.com
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ---- Config ----------------------------------------------------------------

REPO_ROOT   = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / ".github" / "tweeted.json"
SITE_BASE   = "https://kamakoti.github.io/prakashanam"
IST         = timezone(timedelta(hours=5, minutes=30))

# Directories to skip when scanning for event pages
SKIP_DIRS = {".git", ".github", "node_modules", "_site", "assets"}

# How far in the future to schedule the calendar event start
# (IFTTT polls roughly every 15 min for free accounts; 10 min buffer is safe)
START_OFFSET_MINUTES = 10
EVENT_DURATION_MINUTES = 5

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ---- Front-matter parsing --------------------------------------------------

def parse_front_matter(md_path: Path) -> dict | None:
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None


def iter_event_pages(root: Path):
    for md_path in root.rglob("index.md"):
        if any(part in SKIP_DIRS for part in md_path.parts):
            continue
        fm = parse_front_matter(md_path)
        if fm and "date" in fm:
            yield md_path, fm


# ---- Ledger ----------------------------------------------------------------

def load_ledger() -> dict:
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("WARNING: tweeted.json malformed; starting fresh.", file=sys.stderr)
    return {"tweeted": {}}


def save_ledger(ledger: dict) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(
        json.dumps(ledger, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ---- Tweet composition -----------------------------------------------------

def folder_key(md_path: Path) -> str:
    return str(md_path.parent.relative_to(REPO_ROOT)).replace("\\", "/")


def event_url(md_path: Path) -> str:
    return f"{SITE_BASE}/{folder_key(md_path)}/"


def cover_url(md_path: Path) -> str:
    """Return the public URL to cover.jpg if it exists, else empty string."""
    cover_path = md_path.parent / "cover.jpg"
    if cover_path.exists():
        return f"{SITE_BASE}/{folder_key(md_path)}/cover.jpg"
    return ""


def pretty_date(d) -> str:
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    return d.strftime("%d %b %Y")


def compose_tweet(fm: dict, md_path: Path) -> str:
    en = (fm.get("title") or {}).get("en", {}) if isinstance(fm.get("title"), dict) else {}
    desc  = (en.get("desc")  or "").strip()
    tithi = (en.get("tithi") or "").strip()

    date_str = pretty_date(fm["date"])
    url      = event_url(md_path)

    lines = ["Tomorrow:", ""]
    if desc:
        lines.append(desc)

    meta = date_str
    if tithi:
        meta += f" · {tithi}"
    lines.append(meta)
    lines.append("")
    lines.append(url)
    lines.append("")
    lines.append("#adyatithi #अद्यतिथिः #Kamakoti @KanchiMatham")

    tweet = "\n".join(lines)

    if len(tweet) > 280 and tithi:
        idx = lines.index(meta)
        lines[idx] = date_str
        tweet = "\n".join(lines)
    if len(tweet) > 280 and desc:
        lines = [l for l in lines if l != desc]
        tweet = "\n".join(lines)
    return tweet


# ---- Google Calendar -------------------------------------------------------

def get_calendar_service():
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def create_event(service, calendar_id: str, summary: str, description: str,
                 location: str) -> str:
    """Create a short event starting shortly in the future. Returns event id."""
    start = datetime.now(IST) + timedelta(minutes=START_OFFSET_MINUTES)
    end   = start + timedelta(minutes=EVENT_DURATION_MINUTES)

    body = {
        "summary":     summary,        # shows up on the calendar; not used by IFTTT
        "description": description,    # -> tweet body
        "location":    location,       # -> image URL for IFTTT "Where" field
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Kolkata"},
        "end":   {"dateTime": end.isoformat(),   "timeZone": "Asia/Kolkata"},
        # No attendees, no notifications — silent queue only.
        "reminders": {"useDefault": False},
    }
    created = service.events().insert(calendarId=calendar_id, body=body).execute()
    return created["id"]


# ---- Main ------------------------------------------------------------------

def main() -> int:
    calendar_id = os.environ["CALENDAR_ID"]
    tomorrow = (datetime.now(IST) + timedelta(days=0)).date()
    print(f"Looking for events on {tomorrow.isoformat()} (IST tomorrow)")

    ledger  = load_ledger()
    tweeted = ledger.setdefault("tweeted", {})

    candidates = []
    for md_path, fm in iter_event_pages(REPO_ROOT):
        event_date = fm["date"]
        if isinstance(event_date, str):
            try:
                event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                print(event_date)
            except ValueError:
                print(f"  skip {md_path}: unparseable date {fm['date']!r}")
                continue
        if event_date != tomorrow:
            continue

        folder = folder_key(md_path)
        key = f"{folder}@{event_date.isoformat()}"
        if key in tweeted:
            print(f"  skip {key}: already queued at {tweeted[key].get('queued_at')}")
            continue
        candidates.append((md_path, fm, key, event_date))

    if not candidates:
        print("No new events for tomorrow. Done.")
        return 0

    service = get_calendar_service()

    for md_path, fm, key, event_date in candidates:
        tweet_text = compose_tweet(fm, md_path)
        image_url  = cover_url(md_path)
        summary    = f"[tweet] {fm.get('simple_title', folder_key(md_path))}"

        print(f"\nQueuing {key}:")
        print(f"  summary : {summary}")
        print(f"  location: {image_url or '(none)'}")
        print(f"  body    :\n{tweet_text}\n")

        try:
            event_id = create_event(
                service, calendar_id,
                summary=summary,
                description=tweet_text,
                location=image_url,
            )
        except Exception as exc:
            print(f"  FAILED to create calendar event for {key}: {exc}", file=sys.stderr)
            continue

        tweeted[key] = {
            "queued_at":        datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "calendar_event":   event_id,
            "event_date":       event_date.isoformat(),
        }
        print(f"  queued as calendar event {event_id}")

    save_ledger(ledger)
    print(f"\nLedger updated: {LEDGER_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
