"""SMTP sender — pipes drafts to your inbox for review."""
from __future__ import annotations
import os, smtplib, ssl
from email.message import EmailMessage


def send_to_me(subject: str, body: str, attachments: list[str] | None = None) -> dict:
    msg = EmailMessage()
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = os.environ.get("NOTIFY_TO", os.environ["SMTP_FROM"])
    msg["Subject"] = f"[grad-agent] {subject}"
    msg.set_content(body)
    for path in attachments or []:
        try:
            with open(path, "rb") as f:
                data = f.read()
            msg.add_attachment(
                data, maintype="application", subtype="octet-stream",
                filename=os.path.basename(path),
            )
        except Exception as e:
            msg.add_alternative(f"[attach fail {path}: {e}]", subtype="plain")
    ctx = ssl.create_default_context()
    host = os.environ["SMTP_SERVER"]
    user = os.environ["SMTP_USERNAME"]
    pw = os.environ["SMTP_PASSWORD"]
    last_err = None
    for port, use_ssl in [(465, True), (587, False)]:
        try:
            if use_ssl:
                with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
                    s.login(user, pw); s.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=30) as s:
                    s.ehlo(); s.starttls(context=ctx); s.ehlo()
                    s.login(user, pw); s.send_message(msg)
            return {"sent_to": msg["To"], "subject": msg["Subject"], "port": port}
        except Exception as e:
            last_err = f"port {port}: {e}"
    raise RuntimeError(f"SMTP failed on all ports. {last_err}")
