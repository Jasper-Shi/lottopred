from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def should_alert(ev: dict, cfg: dict) -> bool:
    n = cfg["notifications"]
    return ev["final_6_hits"] >= n.get("min_final_hits", 4) or ev["top_12_hits"] >= n.get("min_top12_hits", 5)


def send_email(subject: str, body: str) -> bool:
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]
    if not all(os.getenv(k) for k in required):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    msg.set_content(body)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"]), timeout=30) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
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
