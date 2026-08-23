from __future__ import annotations

import io
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .domain import Draw

DATE_RE = re.compile(
    r"(?P<date>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})\s+"
    r"(?P<n1>\d{1,2})\s+(?P<n2>\d{1,2})\s+(?P<n3>\d{1,2})\s+(?P<n4>\d{1,2})\s+(?P<n5>\d{1,2})\s+(?P<n6>\d{1,2})\s+(?P<bonus>\d{1,2})"
)
RECENT_RE = re.compile(
    r"(?P<date>(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})"
    r".*?CLASSIC DRAW\s+(?P<n1>\d{1,2})\s+(?P<n2>\d{1,2})\s+(?P<n3>\d{1,2})\s+(?P<n4>\d{1,2})\s+(?P<n5>\d{1,2})\s+(?P<n6>\d{1,2})\s+Bonus\s+(?P<bonus>\d{1,2})",
    re.DOTALL | re.IGNORECASE,
)
BRIDGE_DATE_RE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"\d{1,2}(?:st|nd|rd|th)?\s+\d{4}", re.IGNORECASE
)


def parse_wclc_text(text: str) -> list[Draw]:
    normalized = re.sub(r"\s+", " ", text)
    raw = []
    for m in DATE_RE.finditer(normalized):
        dt = datetime.strptime(m.group("date"), "%B %d, %Y").date()
        nums = tuple(int(m.group(f"n{i}")) for i in range(1, 7))
        raw.append([dt, nums, int(m.group("bonus"))])
    for i in range(1, len(raw) - 1):
        prev_dt, cur_dt, next_dt = raw[i - 1][0], raw[i][0], raw[i + 1][0]
        if prev_dt.year == next_dt.year and cur_dt.year != prev_dt.year:
            try:
                candidate = cur_dt.replace(year=prev_dt.year)
            except ValueError:
                continue
            if prev_dt < candidate < next_dt:
                raw[i][0] = candidate
    draws, seen = [], set()
    for dt, nums, bonus in raw:
        try:
            draw = Draw(dt, nums, bonus)
        except ValueError:
            continue
        if draw.draw_date in seen:
            raise RuntimeError(f"Duplicate historical draw date after chronology repair: {draw.draw_date}")
        draws.append(draw)
        seen.add(draw.draw_date)
    return sorted(draws, key=lambda d: d.draw_date)


def fetch_wclc_archive(url: str, timeout: int = 60) -> list[Draw]:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "lotto649-research/0.1"})
    r.raise_for_status()
    if "pdf" not in r.headers.get("content-type", "").lower() and not r.content.startswith(b"%PDF"):
        raise RuntimeError("WCLC since-inception source is no longer a PDF")
    reader = PdfReader(io.BytesIO(r.content))
    draws = parse_wclc_text("\n".join(page.extract_text() or "" for page in reader.pages))
    if len(draws) < 1000:
        raise RuntimeError(f"Parsed only {len(draws)} archive draws; source format may have changed")
    return draws


def parse_wclc_recent_html(html: str) -> list[Draw]:
    text = re.sub(r"\s+", " ", BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    draws, seen = [], set()
    for m in RECENT_RE.finditer(text):
        dt = datetime.strptime(m.group("date"), "%A, %B %d, %Y").date()
        nums = tuple(int(m.group(f"n{i}")) for i in range(1, 7))
        try:
            d = Draw(dt, nums, int(m.group("bonus")))
        except ValueError:
            continue
        if d.draw_date not in seen:
            draws.append(d)
            seen.add(d.draw_date)
    return sorted(draws, key=lambda d: d.draw_date)


def fetch_wclc_recent_draws(url: str, timeout: int = 60) -> list[Draw]:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "lotto649-research/0.1"})
    r.raise_for_status()
    draws = parse_wclc_recent_html(r.text)
    if not draws:
        raise RuntimeError("Could not parse recent WCLC results; source format may have changed")
    return draws


def _parse_bridge_date(value: str) -> date:
    value = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", value, flags=re.IGNORECASE)
    return datetime.strptime(value, "%A %B %d %Y").date()


def parse_lottonet_year_html(html: str) -> list[Draw]:
    """Parse lotto.net annual archives used only to bridge the lagging WCLC PDF.

    The final seven 1..49 integer tokens before each draw's `Bonus` label are
    interpreted as six main numbers plus bonus. Overlap with WCLC is conflict-
    checked, so a disagreement stops the pipeline instead of silently training.
    """
    text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    matches = list(BRIDGE_DATE_RE.finditer(text))
    draws = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segment = text[m.end():end]
        bonus_pos = re.search(r"\bBonus\b", segment, re.IGNORECASE)
        if not bonus_pos:
            continue
        pre_bonus = segment[:bonus_pos.start()]
        tokens = [int(x) for x in re.findall(r"(?<![\d,])\d{1,2}(?![\d,])", pre_bonus)]
        tokens = [x for x in tokens if 1 <= x <= 49]
        if len(tokens) < 7:
            continue
        balls = tokens[-7:]
        try:
            draws.append(Draw(_parse_bridge_date(m.group(0)), tuple(balls[:6]), balls[6]))
        except ValueError:
            continue
    by_date = {d.draw_date: d for d in draws}
    result = [by_date[k] for k in sorted(by_date)]
    if len(result) < 10:
        raise RuntimeError(f"Parsed only {len(result)} bridge draws; lotto.net format may have changed")
    return result


def fetch_lottonet_year(url: str, timeout: int = 60) -> list[Draw]:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "lotto649-research/0.1"})
    r.raise_for_status()
    return parse_lottonet_year_html(r.text)


def fetch_bridge_years(url_template: str, start_year: int, end_year: int) -> list[Draw]:
    groups = [fetch_lottonet_year(url_template.format(year=year)) for year in range(start_year, end_year + 1)]
    return merge_draws(*groups)


def merge_draws(*groups: list[Draw]) -> list[Draw]:
    by_date: dict = {}
    for group in groups:
        for d in group:
            existing = by_date.get(d.draw_date)
            if existing and (existing.numbers != d.numbers or existing.bonus != d.bonus):
                raise RuntimeError(
                    f"Source disagreement for {d.draw_date}: "
                    f"{existing.numbers}/{existing.bonus} vs {d.numbers}/{d.bonus}"
                )
            by_date[d.draw_date] = d
    return [by_date[k] for k in sorted(by_date)]


def validate_continuity(draws: list[Draw]) -> None:
    if len(draws) < 4000:
        raise RuntimeError(f"Expected more than 4,000 historical draws; got {len(draws)}")
    dates = [d.draw_date for d in draws]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise RuntimeError("Draw dates are not strictly ordered and unique")
    for a, b in zip(dates, dates[1:]):
        if a.year >= 2000 and (b - a).days > 14:
            raise RuntimeError(f"Suspicious historical gap: {a} -> {b}")


def _require_data_refresh_enabled(cfg: dict) -> None:
    data_cfg = cfg.get("data")
    if not isinstance(data_cfg, dict) or data_cfg.get("refresh_enabled") is not True:
        raise RuntimeError(
            "data refresh is disabled; data.refresh_enabled must be explicitly true"
        )


def refresh_with_sources(existing: list[Draw], cfg: dict) -> list[Draw]:
    _require_data_refresh_enabled(cfg)
    archive = fetch_wclc_archive(cfg["data"]["history_url"])
    bridge = fetch_bridge_years(
        cfg["data"]["bridge_year_url"],
        int(cfg["data"].get("bridge_start_year", 2024)),
        datetime.now().year,
    )
    recent = fetch_wclc_recent_draws(cfg["data"]["recent_url"])
    merged = merge_draws(existing, archive, bridge, recent)
    validate_continuity(merged)
    return merged


def draws_to_frame(draws: list[Draw]) -> pd.DataFrame:
    return pd.DataFrame([
        {"draw_date": d.draw_date.isoformat(), **{f"n{i + 1}": n for i, n in enumerate(d.numbers)}, "bonus": d.bonus}
        for d in draws
    ]).sort_values("draw_date").reset_index(drop=True)


def save_draws(draws: list[Draw], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    draws_to_frame(draws).to_csv(path, index=False)


def load_draws(path: Path) -> list[Draw]:
    df = pd.read_csv(path)
    draws = [
        Draw(
            pd.to_datetime(row["draw_date"]).date(),
            tuple(int(row[f"n{i}"]) for i in range(1, 7)),
            int(row["bonus"]) if not pd.isna(row.get("bonus")) else None,
        )
        for _, row in df.iterrows()
    ]
    validate_continuity(draws)
    return draws
