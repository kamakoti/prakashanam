#!/usr/bin/env python3
"""
Keep AmritaSiddhi/ pointing at the next upcoming occurrence.

Driven by .github/rotation-config.yaml, which is the source-of-truth master
table of all occurrences (past + future). The workflow only manages the
current-event alias — archived AmritaSiddhi-<date>/ folders are never
touched by this script.

Daily behaviour (04:00 IST):
  - Determine `target` = earliest occurrence with date >= today.
  - Read AmritaSiddhi/index.md's current date.
  - If they already match: no-op.
  - Otherwise:
      1. If AmritaSiddhi/ exists AND its date < today AND
         AmritaSiddhi-<that-date>/ does not already exist:
             rename AmritaSiddhi/ -> AmritaSiddhi-<that-date>/  (archive)
      2. Materialise the new AmritaSiddhi/ from `target`:
             mkdir AmritaSiddhi/
             write index.md (English + Tamil front matter)
             copy README.md from most-recent archived AmritaSiddhi-*/
  - Config file is NEVER modified (source of truth is user-maintained).

Notes:
  - cover.jpg is NOT copied — drop a fresh one manually.
  - New folders start with draft: true.
"""

from __future__ import annotations

import re
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT   = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / ".github" / "rotation-config.yaml"
IST         = timezone(timedelta(hours=5, minutes=30))

# Gregorian month names in Tamil script
TAMIL_MONTHS = {
    1: "ஜனவரி",   2: "பிப்ரவரி",  3: "மார்ச்",   4: "ஏப்ரல்",
    5: "மே",       6: "ஜூன்",      7: "ஜூலை",     8: "ஆகஸ்ட்",
    9: "செப்டம்பர்", 10: "அக்டோபர்", 11: "நவம்பர்", 12: "டிசம்பர்",
}

DATE_SUFFIX_RE = re.compile(r"-(\d{4}-\d{2}-\d{2})$")


# ---- Helpers ---------------------------------------------------------------

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


def coerce_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def english_date(d: date) -> str:
    return d.strftime("%Y-%b-%d")


def tamil_date(d: date) -> str:
    return f"{d.year}-{TAMIL_MONTHS[d.month]}-{d.day}"


def find_most_recent_archive(parent_dir: Path, leaf: str) -> Path | None:
    """Return the AmritaSiddhi-YYYY-MM-DD folder with the latest date, or None."""
    prefix = f"{leaf}-"
    candidates = []
    for child in parent_dir.iterdir():
        if not child.is_dir() or not child.name.startswith(prefix):
            continue
        m = DATE_SUFFIX_RE.search(child.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        candidates.append((d, child))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]


# ---- index.md generator ----------------------------------------------------

def make_index_md(leaf: str, folder_cfg: dict, entry: dict, event_date: date) -> str:
    parent = folder_cfg.get("parent", "")
    banner = folder_cfg.get("banner", parent.lower() if parent else "")

    en = entry.get("en", {}) or {}
    ta = entry.get("ta", {}) or {}

    fm = {
        "layout":       "post",
        "date":         event_date.isoformat(),
        "parent":       parent,
        "draft":        True,
        "folder":       leaf,
        "simple_title": en.get("desc", leaf),
        "banner":       banner,
        "title": {
            "en": {
                "desc":  en.get("desc", ""),
                "tithi": en.get("tithi", ""),
                "date":  english_date(event_date),
            },
            "ta": {
                "desc":  ta.get("desc", ""),
                "tithi": ta.get("tithi", ""),
                "date":  tamil_date(event_date),
            },
        },
    }
    fm_yaml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True,
                             default_flow_style=False).rstrip()
    return f"---\n{fm_yaml}\n---\n"


# ---- Main ------------------------------------------------------------------

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"No config at {CONFIG_PATH}; nothing to do.")
        return {}
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def pick_target(occurrences: list, today: date) -> tuple[dict, date] | None:
    """Return (entry, event_date) for earliest occurrence with date >= today."""
    upcoming = []
    for e in occurrences:
        d = coerce_date(e.get("date"))
        if d is None:
            print(f"  WARNING: unparseable date in occurrence {e!r}; skipped")
            continue
        if d >= today:
            upcoming.append((d, e))
    if not upcoming:
        return None
    upcoming.sort(key=lambda t: t[0])
    d, e = upcoming[0]
    return e, d


def main() -> int:
    today = datetime.now(IST).date()
    print(f"Rotation check for IST today: {today.isoformat()}")

    cfg = load_config()
    if not cfg:
        return 0

    for name, folder_cfg in cfg.items():
        rel_path      = folder_cfg.get("folder_path", name)
        leaf          = rel_path.rsplit("/", 1)[-1]
        folder_path   = REPO_ROOT / rel_path
        parent_dir    = folder_path.parent
        index_path    = folder_path / "index.md"
        occurrences   = folder_cfg.get("occurrences") or []

        target = pick_target(occurrences, today)
        if target is None:
            print(f"  {name}: no upcoming occurrences (today or later); skipping")
            continue
        target_entry, target_date = target

        # Read current folder's date, if it exists.
        current_date = None
        if index_path.exists():
            fm = parse_front_matter(index_path)
            if fm and "date" in fm:
                current_date = coerce_date(fm["date"])

        if current_date == target_date:
            print(f"  {name}: already at {target_date}; no change")
            continue

        print(f"  {name}: current={current_date}, target={target_date}")

        # If the current folder exists AND its date is past, archive it.
        # If its date is future (edge case: config edited to introduce an earlier
        # event ahead of the current one), we don't archive under a future date;
        # we'd overwrite it, which is destructive — skip and warn.
        if folder_path.exists():
            if current_date is None:
                print(f"  {name}: current folder has no parseable date; "
                      f"refusing to touch it")
                continue
            if current_date >= today:
                print(f"  {name}: current folder's date {current_date} is not "
                      f"yet past; refusing to archive (config may have been "
                      f"edited to introduce an earlier occurrence)")
                continue

            archive_path = parent_dir / f"{leaf}-{current_date.isoformat()}"
            if archive_path.exists():
                print(f"  {name}: archive {archive_path.name} already exists; "
                      f"skipping to avoid clobber")
                continue
            print(f"  {name}: archiving -> {archive_path.name}")
            folder_path.rename(archive_path)

        # Materialise the target as the new current folder.
        folder_path.mkdir(parents=True, exist_ok=False)
        (folder_path / "index.md").write_text(
            make_index_md(leaf, folder_cfg, target_entry, target_date),
            encoding="utf-8",
        )
        print(f"  {name}: new index.md written for {target_date}")

        # Copy README.md and cover.jpg from most recent archive.
        recent_archive = find_most_recent_archive(parent_dir, leaf)
        if recent_archive is not None:
            for filename in ("README.md", "cover.jpg"):
                src = recent_archive / filename
                if src.exists():
                    shutil.copy2(src, folder_path / filename)
                    print(f"  {name}: {filename} copied from {recent_archive.name}")
                else:
                    print(f"  {name}: WARNING - no {filename} in {recent_archive.name}")
        else:
            print(f"  {name}: WARNING - no archived folder to copy assets from")

    return 0


if __name__ == "__main__":
    sys.exit(main())
