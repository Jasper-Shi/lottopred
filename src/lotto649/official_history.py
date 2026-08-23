"""Offline parsing and coverage checks for official Loto-Québec 6/49 history."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from hashlib import sha256
import json
import re

from bs4 import BeautifulSoup

from .domain import Draw


LOTTO649_INCEPTION = date(1982, 6, 12)
LOTTO649_TWICE_WEEKLY_START = date(1985, 9, 11)
_CLASSIC_DRAW_TEXT_RE = re.compile(
    r"^([0-9]{1,2})\s+([0-9]{1,2})\s+([0-9]{1,2})\s+"
    r"([0-9]{1,2})\s+([0-9]{1,2})\s+([0-9]{1,2})\s*"
    r"\(\s*([0-9]{1,2})\s*\)$"
)


def _validated_official_draw(draw: Draw, index: int) -> Draw:
    if not isinstance(draw, Draw) or type(draw.draw_date) is not date:
        raise RuntimeError(f"Official history row {index} violates Draw contract")
    if draw.bonus is None:
        raise RuntimeError(f"Official history row {draw.draw_date} has no bonus number")
    try:
        canonical = Draw(draw.draw_date, draw.numbers, draw.bonus)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Official history row {draw.draw_date} violates Draw contract"
        ) from exc
    if canonical != draw:
        raise RuntimeError(
            f"Official history row {draw.draw_date} violates Draw contract"
        )
    return canonical


def _validated_ordered_official_draws(draws: Sequence[Draw]) -> list[Draw]:
    validated = [
        _validated_official_draw(draw, index) for index, draw in enumerate(draws)
    ]
    ordered = sorted(validated, key=lambda draw: draw.draw_date)
    if len({draw.draw_date for draw in ordered}) != len(ordered):
        raise RuntimeError("Cannot hash official history with a duplicate date")
    return ordered


def canonical_official_text_rows_sha256(draws: Sequence[Draw]) -> str:
    """Hash frozen source-collection lines as ``date,NN,...,BB\n``."""
    ordered = _validated_ordered_official_draws(draws)
    lines = []
    for draw in ordered:
        balls = ",".join(f"{value:02d}" for value in (*draw.numbers, draw.bonus))
        lines.append(f"{draw.draw_date.isoformat()},{balls}\n")
    return sha256("".join(lines).encode("utf-8")).hexdigest()


def canonical_official_rows_sha256(draws: Sequence[Draw]) -> str:
    """Hash official rows with the frozen reconciliation-compatible encoding.

    Rows are sorted by date, represented as dictionaries with ISO ``draw_date``,
    an integer ``numbers`` array, and integer ``bonus``, then encoded using
    UTF-8 JSON with sorted keys, no insignificant whitespace, Unicode preserved,
    and non-finite floats forbidden. The SHA-256 is lowercase hexadecimal.
    """
    ordered = _validated_ordered_official_draws(draws)
    rows = [
        {
            "draw_date": draw.draw_date.isoformat(),
            "numbers": list(draw.numbers),
            "bonus": draw.bonus,
        }
        for draw in ordered
    ]
    encoded = json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def expected_lotto649_draw_dates(through: date) -> list[date]:
    """Return the exact scheduled 6/49 dates from inception through ``through``."""
    dates = []
    draw_date = LOTTO649_INCEPTION
    while draw_date < LOTTO649_TWICE_WEEKLY_START and draw_date <= through:
        dates.append(draw_date)
        draw_date += timedelta(days=7)

    draw_date = LOTTO649_TWICE_WEEKLY_START
    while draw_date <= through:
        dates.append(draw_date)
        draw_date += timedelta(days=3 if draw_date.weekday() == 2 else 4)
    return dates


def validate_complete_official_history(draws: Sequence[Draw], through: date) -> None:
    """Fail unless ``draws`` is one valid official row per scheduled date."""
    by_date = {}
    for index, draw in enumerate(draws):
        draw = _validated_official_draw(draw, index)
        existing = by_date.get(draw.draw_date)
        if existing is not None:
            kind = "duplicate" if existing == draw else "conflicting"
            raise RuntimeError(
                f"Official history contains {kind} date: {draw.draw_date}"
            )
        by_date[draw.draw_date] = draw

    expected = set(expected_lotto649_draw_dates(through))
    actual = set(by_date)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        missing_text = ",".join(value.isoformat() for value in missing[:5]) or "none"
        extra_text = ",".join(value.isoformat() for value in extra[:5]) or "none"
        raise RuntimeError(
            "Official history date set mismatch: "
            f"missing={missing_text}; extra={extra_text}"
        )


def parse_lotoquebec_detail_html(html: str, expected_date: date) -> Draw:
    """Parse one 6/49 classic draw from a Loto-Québec detail widget."""
    soup = BeautifulSoup(html, "html.parser")
    date_nodes = soup.select("#dateAffichee")
    if len(date_nodes) != 1:
        raise RuntimeError(
            f"Official detail has {len(date_nodes)} displayed dates, expected 1"
        )
    raw_date = date_nodes[0].get_text(strip=True)
    try:
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw_date) is None:
            raise ValueError("date is not strict ISO-8601")
        draw_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise RuntimeError(
            f"Official detail has malformed draw date: {raw_date!r}"
        ) from exc
    if draw_date != expected_date:
        raise RuntimeError(
            f"Official detail date {draw_date} does not match {expected_date}"
        )

    blocks = soup.select(".lqZoneProduit.principal.lotto-6-49 .numeros.tirageClassique")
    if len(blocks) != 1:
        raise RuntimeError(
            f"Official detail has {len(blocks)} 6/49 classic blocks, expected 1"
        )
    block = blocks[0]
    main_nodes = block.select(".num:not(.complementaire)")
    bonus_nodes = block.select(".num.complementaire")
    if len(main_nodes) != 6 or len(bonus_nodes) != 1:
        raise RuntimeError(
            "Official detail must contain exactly 6 main numbers and 1 bonus; "
            f"got {len(main_nodes)}+{len(bonus_nodes)}"
        )
    ball_texts = [node.get_text(strip=True) for node in (*main_nodes, *bonus_nodes)]
    if any(re.fullmatch(r"[0-9]{1,2}", value) is None for value in ball_texts):
        raise RuntimeError(
            f"Official detail row {draw_date} has a malformed ball value"
        )
    main = [int(value) for value in ball_texts[:6]]
    try:
        return Draw(draw_date, tuple(main), int(ball_texts[6]))
    except ValueError as exc:
        raise RuntimeError(
            f"Official detail row {draw_date} has invalid 6/49 values"
        ) from exc


def parse_lotoquebec_annual_html(html: str, expected_year: int) -> list[Draw]:
    """Parse classic 6/49 rows from a Loto-Québec annual-results widget."""
    soup = BeautifulSoup(html, "html.parser")
    draws = []
    by_date = {}
    for row in soup.find_all("tr"):
        date_cells = row.find_all("td", class_="date")
        if not date_cells:
            continue
        if len(date_cells) != 1:
            raise RuntimeError(
                f"Official history row has {len(date_cells)} date cells, expected 1"
            )
        date_cell = date_cells[0]
        raw_date = date_cell.get_text(strip=True)
        try:
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw_date) is None:
                raise ValueError("date is not strict ISO-8601")
            draw_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise RuntimeError(
                f"Official history row has malformed draw date: {raw_date!r}"
            ) from exc
        if draw_date.year != expected_year:
            raise RuntimeError(
                f"Official history row {draw_date} is outside expected year "
                f"{expected_year}"
            )
        numbered_blocks = row.select(
            ".numerosGagnants.principal, .numerosGangnants.principal"
        )
        classic_candidates = []
        for block in numbered_blocks:
            text = re.sub(r"\s+", " ", block.get_text(" ", strip=True)).strip()
            match = _CLASSIC_DRAW_TEXT_RE.fullmatch(text)
            if match is not None:
                classic_candidates.append((block, match))
        if len(classic_candidates) != 1:
            if len(numbered_blocks) == 1:
                raise RuntimeError(
                    f"Official history row {draw_date} has a malformed ball value"
                )
            raise RuntimeError(
                f"Official history row {draw_date} has {len(classic_candidates)} "
                "classic draw blocks, expected 1"
            )
        _, classic_match = classic_candidates[0]
        balls = [int(value) for value in classic_match.groups()]
        try:
            draw = Draw(draw_date, tuple(balls[:6]), balls[6])
        except ValueError as exc:
            raise RuntimeError(
                f"Official history row {draw_date} has invalid 6/49 values"
            ) from exc
        existing = by_date.get(draw_date)
        if existing is not None:
            if existing == draw:
                raise RuntimeError(f"Duplicate official history date: {draw_date}")
            raise RuntimeError(f"Conflicting official history rows: {draw_date}")
        draws.append(draw)
        by_date[draw_date] = draw
    if not draws:
        raise RuntimeError("Official annual widget contains no official draw rows")
    return sorted(draws, key=lambda draw: draw.draw_date)
