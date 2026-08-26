from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import os
import re
import smtplib
from email.message import EmailMessage
from zoneinfo import ZoneInfo


_OID_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_DRAW_TIME_ZONE = ZoneInfo("America/Toronto")


@dataclass(frozen=True)
class PublishedPreDrawRecommendation:
    """One ensemble ticket proven to exist in an immutable artifact commit."""

    target_draw_date: date
    generated_at: datetime
    model_name: str
    model_version: str
    final_combination: tuple[int, int, int, int, int, int]
    snapshot_path: str
    snapshot_sha256: str
    artifact_commit: str

    def __post_init__(self) -> None:
        expected_path = (
            f"predictions/{self.target_draw_date.isoformat()}__"
            f"ensemble__{self.model_version}.json"
        )
        try:
            offset = self.generated_at.utcoffset()
        except (AttributeError, OverflowError, TypeError, ValueError) as exc:
            raise ValueError("pre-draw recommendation timestamp is invalid") from exc
        if (
            type(self.target_draw_date) is not date
            or type(self.generated_at) is not datetime
            or self.generated_at.microsecond != 0
            or offset is None
            or self.generated_at.astimezone(_DRAW_TIME_ZONE).date()
            >= self.target_draw_date
            or self.model_name != "ensemble"
            or type(self.model_version) is not str
            or _VERSION_RE.fullmatch(self.model_version) is None
            or type(self.final_combination) is not tuple
            or len(self.final_combination) != 6
            or any(
                type(number) is not int or not 1 <= number <= 49
                for number in self.final_combination
            )
            or len(set(self.final_combination)) != 6
            or self.final_combination != tuple(sorted(self.final_combination))
            or self.snapshot_path != expected_path
            or _SHA256_RE.fullmatch(self.snapshot_sha256) is None
            or _OID_RE.fullmatch(self.artifact_commit) is None
        ):
            raise ValueError("pre-draw recommendation is invalid")


def should_alert(ev: dict, cfg: dict) -> bool:
    n = cfg["notifications"]
    return ev["final_6_hits"] >= n.get("min_final_hits", 4) or ev[
        "top_12_hits"
    ] >= n.get("min_top12_hits", 5)


def _deliver_email(
    subject: str,
    body: str,
    *,
    username: str,
    password: str,
    host: str,
    port: int,
    sender: str,
    recipient: str,
) -> bool:
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

    return _deliver_email(
        subject,
        body,
        username=username,
        password=password,
        host=os.getenv("SMTP_HOST") or "smtp.gmail.com",
        port=int(os.getenv("SMTP_PORT") or "587"),
        sender=os.getenv("EMAIL_FROM") or username,
        recipient=os.getenv("EMAIL_TO") or username,
    )


def send_pre_draw_recommendation(
    recommendation: PublishedPreDrawRecommendation,
) -> bool:
    """Attempt one fixed-route Chinese email for an already-published ticket."""

    if type(recommendation) is not PublishedPreDrawRecommendation:
        raise TypeError("published pre-draw recommendation has the wrong type")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    if not username or not password:
        return False
    numbers = "、".join(f"{number:02d}" for number in recommendation.final_combination)
    subject = (
        f"LOTTO 6/49 开奖前实验号码 — {recommendation.target_draw_date.isoformat()}"
    )
    body = (
        f"开奖日期：{recommendation.target_draw_date.isoformat()}\n"
        f"实验参考号码：{numbers}\n"
        f"模型：{recommendation.model_name} {recommendation.model_version}\n"
        f"生成时间：{recommendation.generated_at.isoformat()}\n"
        f"预测快照：{recommendation.snapshot_path}\n"
        f"固定提交：{recommendation.artifact_commit}\n"
        "\n"
        "这组号码是在开奖前生成并固定的实验结果，不保证中奖。\n"
        "如决定购买，只应使用预先设定、可承受损失的小额预算。\n"
    )
    return _deliver_email(
        subject,
        body,
        username=username,
        password=password,
        host="smtp.gmail.com",
        port=587,
        sender=username,
        recipient=username,
    )


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
