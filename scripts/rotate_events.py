#!/usr/bin/env python3
"""
Keep AmritaSiddhi/ pointing at the next upcoming occurrence.

Driven by .github/rotation-config.yaml, which is the source-of-truth master
table of all occurrences (past + future).

Daily behaviour (04:00 IST):
  - Determine target = earliest occurrence with date >= today.
  - Read AmritaSiddhi/index.md's current date.
  - If current date is past and != target:
      1. Create fresh AmritaSiddhi-<current-date>/ folder.
      2. Copy index.md, README.md, cover.jpg from AmritaSiddhi/ into it.
      3. Overwrite AmritaSiddhi/index.md with the new event's front matter.
  - PDFs and any other files inside AmritaSiddhi/ stay untouched — they
    are constant across events and only live in the current folder.
  - README.md and cover.jpg are ALSO constant, but get duplicated into
    archives so the archive pages still render correctly.

Config file is NEVER modified — source of truth is user-maintained.
"""

from __future__ import annotations

import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT   = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / ".github" / "rotation-config.yaml"
IST         = timezone(timedelta(hours=5, minutes=30))

# Files copied from AmritaSiddhi/ into the archive on rotation.
# Files NOT in this list (PDFs, any other assets) stay put in AmritaSiddhi/.
ARCHIVED_FILES = ("index.md", "README.md", "cover.jpg")

# Gregorian month names in Tamil script
TAMIL_MONTHS = {
    1: "ஜனவரி",   2: "பிப்ரவரி",  3: "மார்ச்",   4: "ஏப்ரல்",
    5: "மே",       6: "ஜூன்",      7: "ஜூலை",     8: "ஆகஸ்ட்",
    9: "செப்டம்பர்", 10: "அக்டோபர்", 11: "நவம்பர்", 12: "டிசம்பர்",
}


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

    exit_code = 0

    for name, folder_cfg in cfg.items():
        rel_path      = folder_cfg.get("folder_path", name)
        leaf          = rel_path.rsplit("/", 1)[-1]
        folder_path   = REPO_ROOT / rel_path
        parent_dir    = folder_path.parent
        index_path    = folder_path / "index.md"
        occurrences   = folder_cfg.get("occurrences") or []

        target = pick_target(occurrences, today)
        if target is None:
            print(f"  {name}: no upcoming occurrences; skipping")
            continue
        target_entry, target_date = target

        if not index_path.exists():
            print(f"  {name}: {index_path} missing; skipping")
            continue

        fm = parse_front_matter(index_path)
        if not fm or "date" not in fm:
            print(f"  {name}: no parseable date in front matter; skipping")
            continue

        current_date = coerce_date(fm["date"])
        if current_date is None:
            print(f"  {name}: unparseable date {fm['date']!r}; skipping")
            continue

        if current_date == target_date:
            print(f"  {name}: already at {target_date}; no change")
            continue

        if current_date >= today:
            print(f"  {name}: current date {current_date} is not yet past; "
                  f"refusing to rotate (config may have been edited)")
            continue

        # Current is past AND != target. Rotate.
        archive_path = parent_dir / f"{leaf}-{current_date.isoformat()}"
        if archive_path.exists():
            print(f"  {name}: archive {archive_path.name} already exists; "
                  f"skipping to avoid clobber (manual intervention needed)")
            exit_code = 1
            continue

        print(f"  {name}: current={current_date}, target={target_date}")
        print(f"  {name}: creating archive {archive_path.name}")
        archive_path.mkdir(parents=True)

        # Copy the standard files. Any file missing from source is a WARNING
        # but does not abort — the source file being missing was already a
        # site-rendering issue that the user needs to fix separately.
        for filename in ARCHIVED_FILES:
            src = folder_path / filename
            if src.exists():
                shutil.copy2(src, archive_path / filename)
                print(f"  {name}: copied {filename} -> {archive_path.name}/")
            else:
                print(f"  {name}: WARNING - {filename} missing from "
                      f"{folder_path.name}/; archive will lack it too",
                      file=sys.stderr)

        # Overwrite the current index.md with the new event's front matter.
        # README.md, cover.jpg, PDFs and everything else in AmritaSiddhi/
        # remain untouched — they're constant across events.
        index_path.write_text(
            make_index_md(leaf, folder_cfg, target_entry, target_date),
            encoding="utf-8",
        )
        print(f"  {name}: index.md updated for {target_date}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())