from __future__ import annotations

from datetime import datetime
import warnings

import requests

from .data import (
    fetch_bridge_years,
    fetch_wclc_archive,
    fetch_wclc_recent_draws,
    merge_draws,
    validate_continuity,
)
from .domain import Draw


def _require_data_refresh_enabled(cfg: dict) -> None:
    data_cfg = cfg.get("data")
    if not isinstance(data_cfg, dict) or data_cfg.get("refresh_enabled") is not True:
        raise RuntimeError(
            "data refresh is disabled; data.refresh_enabled must be explicitly true"
        )


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

    recent_by_date = {d.draw_date: d for d in recent}
    for d in bridge_window:
        official = recent_by_date.get(d.draw_date)
        if official and (official.numbers != d.numbers or official.bonus != d.bonus):
            raise RuntimeError(
                f"Bridge/current-WCLC disagreement for {d.draw_date}: "
                f"bridge={d.numbers}/{d.bonus} official={official.numbers}/{official.bonus}"
            )

    selected = merge_draws(cutoff_archive, bridge_window, recent)

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
    _require_data_refresh_enabled(cfg)
    bridge_start_year = int(cfg["data"].get("bridge_start_year", 2024))
    archive = fetch_wclc_archive(cfg["data"]["history_url"])

    # lotto.net is only a bridge for the lagging WCLC archive, not the source of
    # truth for today's result. A transient bridge outage must not prevent a live
    # cycle when the committed chronology is already continuous and the official
    # WCLC recent page is available. If committed data is insufficient, the final
    # continuity check still fails rather than silently inventing missing draws.
    try:
        bridge = fetch_bridge_years(
            cfg["data"]["bridge_year_url"],
            bridge_start_year,
            datetime.now().year,
        )
    except (requests.RequestException, TimeoutError) as exc:
        warnings.warn(f"Bridge source unavailable; continuing with committed/WCLC data: {exc}")
        bridge = []

    recent = fetch_wclc_recent_draws(cfg["data"]["recent_url"])
    return reconcile_by_era(existing, archive, bridge, recent, bridge_start_year)
