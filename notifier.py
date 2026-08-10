"""Telegram message senders."""
from __future__ import annotations

import html
import logging
from collections import defaultdict
from datetime import datetime, timezone

import aiohttp

log = logging.getLogger("arcy-alerter.notifier")

_TG_MAX = 4000  # Telegram max is 4096 — leave a little headroom


async def _send_html(
    session: aiohttp.ClientSession,
    *,
    bot_token: str,
    chat_id: str,
    text: str,
) -> bool:
    api = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with session.post(
            api,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        ) as resp:
            if resp.status >= 400:
                body = await resp.text()
                log.error("Telegram %s: %s", resp.status, body[:300])
                return False
            return True
    except Exception as exc:
        log.error("Telegram send failed: %s", exc)
        return False


async def send_job(
    session: aiohttp.ClientSession,
    *,
    bot_token: str,
    chat_id: str,
    job: dict,
) -> bool:
    """Single-posting alert (legacy --once mode)."""
    company = html.escape(job.get("company", "?"))
    title = html.escape(job.get("title", "?"))
    location = html.escape(job.get("location", "") or "Location not stated")
    department = html.escape(job.get("department", "") or "")
    url = job.get("url", "")

    parts = [
        f"<b>{company}</b> — new role",
        f"<b>{title}</b>",
        f"📍 {location}",
    ]
    if department:
        parts.append(f"🏷 {department}")
    if url:
        parts.append("")
        parts.append(f'<a href="{html.escape(url)}">Apply / view posting</a>')

    return await _send_html(session, bot_token=bot_token, chat_id=chat_id,
                            text="\n".join(parts))


async def send_text(
    session: aiohttp.ClientSession,
    *,
    bot_token: str,
    chat_id: str,
    text: str,
) -> bool:
    api = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with session.post(
            api,
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=20,
        ) as resp:
            return resp.status < 400
    except Exception as exc:
        log.error("Telegram text send failed: %s", exc)
        return False


def _age_label(posted_at) -> str:
    if not posted_at:
        return ""
    try:
        delta = datetime.now(timezone.utc) - posted_at
    except Exception:
        return ""
    days = delta.days
    if days <= 0:
        return "today"
    if days == 1:
        return "1d ago"
    return f"{days}d ago"


def _format_job_line(job: dict) -> str:
    title = html.escape(job.get("title", "?"))
    location = html.escape(job.get("location", "") or "—")
    url = job.get("url", "")
    age = _age_label(job.get("posted_at"))
    label = job.get("_label", "")

    bits = []
    if label:
        bits.append(f"[{html.escape(label)}]")
    bits.append(f"<b>{title}</b>")
    line1 = " ".join(bits)
    line2 = f"   📍 {location}"
    if age:
        line2 += f"  ·  <i>{age}</i>"
    if url:
        line2 += f'  ·  <a href="{html.escape(url)}">apply</a>'
    return line1 + "\n" + line2


def _build_digest_messages(jobs: list[dict], *, max_age_days: int) -> list[str]:
    """Return one or more HTML message bodies fitting Telegram's size cap.

    Sections, top to bottom (every job is in a target region by the time it
    gets here — the split is by city):
      • 🏙 STOCKHOLM
      • ❄️ NORDICS         (rest of Sweden + Norway / Denmark / Finland / Iceland)
      • 🌷 AMSTERDAM / NL
      • 🎡 LONDON / UK
      • ⛰ ZURICH / CH
      • 🇪🇺 REST OF EUROPE  (Dublin / Frankfurt / Paris / … + EU-remote)
    """
    if not jobs:
        return []

    from filters import (is_stockholm_location, is_nordic_location,
                         is_amsterdam_location, is_london_location,
                         is_zurich_location)

    # First matching bucket wins, so a "Stockholm / Amsterdam" posting lands once.
    buckets = [
        ("🏙 STOCKHOLM", is_stockholm_location, []),
        ("❄️ NORDICS", is_nordic_location, []),
        ("🌷 AMSTERDAM / NL", is_amsterdam_location, []),
        ("🎡 LONDON / UK", is_london_location, []),
        ("⛰ ZURICH / CH", is_zurich_location, []),
    ]
    rest_jobs: list[dict] = []
    for j in jobs:
        loc = j.get("location", "") or ""
        for _name, pred, acc in buckets:
            if pred(loc):
                acc.append(j)
                break
        else:
            rest_jobs.append(j)

    today = datetime.now(timezone.utc).strftime("%a %d %b %Y")
    n_companies = len({j.get("company", "?") for j in jobs})
    header = (
        f"<b>🎯 Internship digest — {html.escape(today)}</b>\n"
        f"{len(jobs)} new role(s) across {n_companies} compan(ies), "
        f"posted in the last {max_age_days} day(s)."
    )

    pieces: list[str] = [header, ""]

    def section_pieces(label: str, section_jobs: list[dict]) -> list[str]:
        if not section_jobs:
            return []
        by_company: dict[str, list[dict]] = defaultdict(list)
        for j in section_jobs:
            by_company[j.get("company", "?")].append(j)

        def newest(cjobs):
            ts = [j.get("posted_at") for j in cjobs if j.get("posted_at")]
            return max(ts) if ts else datetime.fromtimestamp(0, tz=timezone.utc)

        company_order = sorted(by_company.keys(),
                               key=lambda c: newest(by_company[c]),
                               reverse=True)
        out = [f"<b>════ {label} ({len(section_jobs)}) ════</b>", ""]
        for c in company_order:
            cjobs = sorted(
                by_company[c],
                key=lambda j: j.get("posted_at") or datetime.fromtimestamp(0, tz=timezone.utc),
                reverse=True,
            )
            out.append(f"━━━ <b>{html.escape(c)}</b> ({len(cjobs)}) ━━━")
            for j in cjobs:
                out.append(_format_job_line(j))
            out.append("")
        return out

    for name, _pred, acc in buckets:
        pieces.extend(section_pieces(name, acc))
    pieces.extend(section_pieces("🇪🇺 REST OF EUROPE", rest_jobs))

    # Greedy split into <=4000-char chunks at piece boundaries.
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = piece if not current else current + "\n" + piece
        if len(candidate) > _TG_MAX:
            if current:
                chunks.append(current)
            current = piece
        else:
            current = candidate
    if current:
        chunks.append(current)

    if len(chunks) > 1:
        chunks = [f"{c}\n\n<i>(part {i+1}/{len(chunks)})</i>"
                  for i, c in enumerate(chunks)]
    return chunks


async def send_digest(
    session: aiohttp.ClientSession,
    *,
    bot_token: str,
    chat_id: str,
    jobs: list[dict],
    max_age_days: int,
) -> int:
    """Send a grouped digest. Returns number of messages sent."""
    chunks = _build_digest_messages(jobs, max_age_days=max_age_days)
    sent = 0
    for chunk in chunks:
        ok = await _send_html(session, bot_token=bot_token, chat_id=chat_id,
                              text=chunk)
        if ok:
            sent += 1
    return sent
