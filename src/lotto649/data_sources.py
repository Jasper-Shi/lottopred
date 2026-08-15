from __future__ import annotations

from datetime import datetime

from .data import (
    fetch_bridge_years,
    fetch_wclc_archive,
    fetch_wclc_recent_draws,
    merge_draws,
    validate_continuity,
)
from .domain import Draw


def reconcile_by_era(
    existing: list[Draw],
    archive: list[Draw],
    bridge: list[Draw],
    recent: list[Draw],
    bridge_start_year: int,
) -> list[Draw]:
    """Build one chronology without trusting PDF text extraction beyond its era.

    WCLC's downloadable since-inception PDF is the preferred historical source,
    but PDF text extraction can occasionally misread a glyph in newer rows. The
    annual HTML bridge is therefore the canonical machine-readable source from
    ``bridge_start_year`` onward, while the current WCLC results page independently
    validates the recent overlap. A disagreement between bridge and current WCLC
    still fails loudly.

    Existing committed data is retained only when it agrees with the selected
    sources for the same date.
    """
    cutoff_archive = [d for d in archive if d.draw_date.year < bridge_start_year]
    bridge_window = [d for d in bridge if d.draw_date.year >= bridge_start_year]

    # This comparison is the important live integrity check. If the third-party
    # bridge disagrees with current official WCLC results, do not proceed.
    recent_by_date = {d.draw_date: d for d in recent}
    for d in bridge_window:
        official = recent_by_date.get(d.draw_date)
        if official and (official.numbers != d.numbers or official.bonus != d.bonus):
            raise RuntimeError(
                f"Bridge/current-WCLC disagreement for {d.draw_date}: "
                f"bridge={d.numbers}/{d.bonus} official={official.numbers}/{official.bonus}"
            )

    selected = merge_draws(cutoff_archive, bridge_window, recent)

    # Existing snapshots/data must never silently override a refreshed source.
    selected_by_date = {d.draw_date: d for d in selected}
    for d in existing:
        refreshed = selected_by_date.get(d.draw_date)
        if refreshed and (refreshed.numbers != d.numbers or refreshed.bonus != d.bonus):
            raise RuntimeError(
                f"Committed-data/source disagreement for {d.draw_date}: "
                f"committed={d.numbers}/{d.bonus} refreshed={refreshed.numbers}/{refreshed.bonus}"
            )

    merged = merge_draws(existing, selected)
    validate_continuity(merged)
    return merged


def refresh_with_sources(existing: list[Draw], cfg: dict) -> list[Draw]:
    bridge_start_year = int(cfg["data"].get("bridge_start_year", 2024))
    archive = fetch_wclc_archive(cfg["data"]["history_url"])
    bridge = fetch_bridge_years(
        cfg["data"]["bridge_year_url"],
        bridge_start_year,
        datetime.now().year,
    )
    recent = fetch_wclc_recent_draws(cfg["data"]["recent_url"])
    return reconcile_by_era(existing, archive, bridge, recent, bridge_start_year)
