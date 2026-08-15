from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def should_alert(ev: dict, cfg: dict) -> bool:
    n = cfg["notifications"]
    return ev["final_6_hits"] >= n.get("min_final_hits", 4) or ev["top_12_hits"] >= n.get("min_top12_hits", 5)


def send_email(subject: str, body: str) -> bool:
    """Send through Gmail-compatible SMTP with only two required secrets.

    Required:
      SMTP_USERNAME: Gmail address
      SMTP_PASSWORD: Google App Password

    Optional overrides:
      SMTP_HOST (default smtp.gmail.com)
      SMTP_PORT (default 587)
      EMAIL_FROM (default SMTP_USERNAME)
      EMAIL_TO (default SMTP_USERNAME)
    """
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    if not username or not password:
        return False

    host = os.getenv("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.getenv("SMTP_PORT") or "587")
    sender = os.getenv("EMAIL_FROM") or username
    recipient = os.getenv("EMAIL_TO") or username

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(msg)
    return True


def send_hit_alert(ev: dict) -> bool:
    subject = f"LOTTO 6/49 model alert — {ev['final_6_hits']}/6 ({ev['model_name']})"
    body = (
        f"Draw: {ev['target_draw_date']}\n"
        f"Model: {ev['model_name']} {ev['model_version']}\n"
        f"Actual: {ev['actual']}\n"
        f"Matched final: {ev['matched_final']}\n"
        f"Final hits: {ev['final_6_hits']}/6\n"
        f"Top-12 hits: {ev['top_12_hits']}/6\n"
        f"Top-18 hits: {ev['top_18_hits']}/6\n"
        f"Brier: {ev['brier_score']:.6f}\n"
        f"Mean actual rank: {ev['mean_actual_rank']:.2f}\n"
    )
    return send_email(subject, body)
