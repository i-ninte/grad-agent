"""Read-only IMAP reply detection.

Scans the user's inbox for messages FROM professors we emailed, arriving
after the send date, and tags the outreach log automatically. Never sends,
never deletes, never marks messages read (BODY.PEEK semantics via fetch of
headers only through search, and we never issue STORE).

Config (all optional; Gmail defaults derived from SMTP settings):
  IMAP_SERVER    default: imap.gmail.com
  IMAP_USERNAME  default: SMTP_USERNAME
  IMAP_PASSWORD  default: SMTP_PASSWORD
"""
from __future__ import annotations
import datetime as _dt
import imaplib
import os

from .. import outreach_log


def _connect() -> imaplib.IMAP4_SSL | None:
    host = os.environ.get("IMAP_SERVER") or "imap.gmail.com"
    user = os.environ.get("IMAP_USERNAME") or os.environ.get("SMTP_USERNAME", "")
    pw = os.environ.get("IMAP_PASSWORD") or os.environ.get("SMTP_PASSWORD", "")
    if not user or not pw:
        return None
    try:
        conn = imaplib.IMAP4_SSL(host, timeout=30)
        conn.login(user, pw)
        conn.select("INBOX", readonly=True)
        return conn
    except Exception:
        return None


def _imap_date(d: _dt.datetime) -> str:
    return d.strftime("%d-%b-%Y")


def ingest() -> dict:
    """Check for replies from every prof we emailed who has not been tagged
    as responded. Returns {checked, replies_found, tagged: [names]}."""
    candidates = []
    for r in outreach_log.list_all(limit=500):
        email_addr = str(r.get("prof_email") or "").strip()
        sent = str(r.get("sent_to_prof_at") or "").strip()
        responded = str(r.get("responded") or "").lower() == "yes"
        if email_addr and "@" in email_addr and sent and not responded:
            candidates.append((r, email_addr, sent))

    if not candidates:
        return {"checked": 0, "replies_found": 0, "tagged": [],
                "note": "no sent rows with an email address awaiting a reply"}

    conn = _connect()
    if conn is None:
        return {"checked": 0, "replies_found": 0, "tagged": [],
                "error": "IMAP unavailable (missing creds or connect failed)"}

    tagged = []
    try:
        for row, email_addr, sent in candidates:
            try:
                sent_dt = _dt.datetime.strptime(sent[:10], "%Y-%m-%d")
            except ValueError:
                continue
            since = _imap_date(sent_dt)
            try:
                status, data = conn.search(
                    None, f'(FROM "{email_addr}" SINCE "{since}")')
            except Exception:
                continue
            ids = (data[0] or b"").split()
            if status == "OK" and ids:
                name = str(row.get("prof_name") or "")
                outreach_log.mark_response(
                    name, "replied",
                    notes=f"auto-detected via IMAP ({len(ids)} message(s))")
                tagged.append(name)
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    return {"checked": len(candidates), "replies_found": len(tagged),
            "tagged": tagged}
