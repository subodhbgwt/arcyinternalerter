"""Add events, spring weeks and other finds from the weekly scout.

The scout (a scheduled Claude task, see SCOUT.md) reads firm pages and
trackers that have no API, writes what it found to a JSON file, and calls:

    python scout_add.py finds.json            # add to tracker + Telegram
    python scout_add.py finds.json --dry-run  # just print

finds.json is a list of objects:
    {"company": "Bain & Company", "title": "Case evening for KTH students",
     "type": "Event" | "Spring week" | "Internship" | "Insight",
     "location": "Stockholm", "when": "2026-11-20", "deadline": "2026-11-16",
     "link": "https://...", "note": "short extra info"}

Each find is keyed on its link, so running it twice never duplicates a row
or a Telegram message.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

from excel_tracker import append_jobs
from notifier import _send_html

ROOT = Path(__file__).resolve().parent
SEEN_FILE = ROOT / "scout_seen.json"
TRACKER_FILE = ROOT / "job_tracker.xlsx"
ICON = {"Event": "🤝", "Spring week": "🌱", "Insight": "🌱", "Internship": "💼"}


def _load_seen() -> set[str]:
    try:
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()


def _to_job(f: dict) -> dict:
    notes = []
    if f.get("when"):
        notes.append(f"when {f['when']}")
    if f.get("deadline"):
        notes.append(f"deadline {f['deadline']}")
    if f.get("note"):
        notes.append(f["note"])
    return {
        "id": "scout:" + f["link"].strip(),
        "company": f.get("company", ""),
        "title": f.get("title", ""),
        "location": f.get("location", ""),
        "url": f["link"].strip(),
        "_label": f.get("type", "Event"),
        "_notes": "; ".join(notes),
    }


def _message(finds: list[dict]) -> str:
    lines = [f"<b>Scout: {len(finds)} new event(s) / programme(s)</b>", ""]
    for f in sorted(finds, key=lambda x: (x.get("deadline") or x.get("when") or "9999")):
        icon = ICON.get(f.get("type", ""), "•")
        extra = " · ".join(x for x in (
            f.get("location"), f.get("when") and f"on {f['when']}",
            f.get("deadline") and f"apply by {f['deadline']}") if x)
        lines.append(f'{icon} <b>{html.escape(f.get("company", ""))}</b>: '
                     f'<a href="{html.escape(f["link"])}">{html.escape(f.get("title", ""))}</a>')
        if extra:
            lines.append(f"    {html.escape(extra)}")
    return "\n".join(lines)


async def main() -> int:
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("finds")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    finds = [f for f in json.loads(Path(a.finds).read_text(encoding="utf-8"))
             if f.get("link")]
    seen = _load_seen()
    new = [f for f in finds if f["link"].strip() not in seen]
    print(f"{len(finds)} find(s), {len(new)} new")
    if not new:
        return 0
    if a.dry_run:
        print(_message(new))
        return 0

    added = append_jobs([_to_job(f) for f in new], TRACKER_FILE)
    print(f"tracker: +{added} row(s)")

    load_dotenv(ROOT / ".env")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    sent = False
    if token and chat:
        async with aiohttp.ClientSession() as s:
            sent = await _send_html(s, bot_token=token, chat_id=chat,
                                    text=_message(new)[:4000])
    print("telegram:", "sent" if sent else "NOT sent")

    seen.update(f["link"].strip() for f in new)
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=0), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
