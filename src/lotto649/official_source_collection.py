"""Retrieve the two immutable official assets for one scheduled draw."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

import requests

from .history_publication import RawSource

MAX_SOURCE_BYTES = 2 * 1024 * 1024
WCLC_URL = "https://www.wclc.com/winning-numbers/lotto-649-extra.htm"
LOTO_QUEBEC_URL_TEMPLATE = (
    "https://loteries.lotoquebec.com/en/lotteries/lotto-6-49-resultats?date={draw_date}"
)
_LOTO_QUEBEC_URL_PREFIX = LOTO_QUEBEC_URL_TEMPLATE.removesuffix("{draw_date}")
_DRAW_TIME_ZONE = ZoneInfo("America/Toronto")


class OfficialSourceCollectionError(ValueError):
    """Raised when the official two-source collection cannot be trusted."""


class OfficialSourceHttpClient(Protocol):
    """Fetch one exact official URL without redirecting or exceeding a limit."""

    def fetch(self, url: str, *, max_bytes: int) -> bytes: ...


class RequestsOfficialSourceHttpClient:
    """HTTPS adapter that returns the exact bounded response body it parsed."""

    def fetch(self, url: str, *, max_bytes: int) -> bytes:
        if type(url) is not str or not _is_canonical_official_url(url):
            raise OfficialSourceCollectionError(
                "request must use one canonical official URL"
            )
        if type(max_bytes) is not int or max_bytes < 1 or max_bytes > MAX_SOURCE_BYTES:
            raise OfficialSourceCollectionError(
                "request size limit must be a bounded positive integer"
            )
        try:
            response_context = requests.get(
                url,
                allow_redirects=False,
                headers={
                    "Accept-Encoding": "identity",
                    "User-Agent": "lotto649-verified-history/1",
                },
                stream=True,
                timeout=(10, 30),
            )
            with response_context as response:
                if response.status_code != 200:
                    raise OfficialSourceCollectionError(
                        "official source response must be HTTP 200 without redirects"
                    )
                if type(response.url) is not str or response.url != url:
                    raise OfficialSourceCollectionError(
                        "official source response must retain the exact requested URL"
                    )
                content_type = response.headers.get("Content-Type")
                if (
                    type(content_type) is not str
                    or content_type.partition(";")[0].strip().lower() != "text/html"
                ):
                    raise OfficialSourceCollectionError(
                        "official source response must use text/html"
                    )
                content_encoding = response.headers.get("Content-Encoding")
                if content_encoding is not None and (
                    type(content_encoding) is not str
                    or content_encoding.strip().lower() != "identity"
                ):
                    raise OfficialSourceCollectionError(
                        "official source response must not use Content-Encoding"
                    )
                content_length = response.headers.get("Content-Length")
                declared_length: int | None = None
                if content_length is not None:
                    if (
                        type(content_length) is not str
                        or not content_length.isascii()
                        or not content_length.isdigit()
                    ):
                        raise OfficialSourceCollectionError(
                            "official source Content-Length is invalid"
                        )
                    normalized_length = content_length.lstrip("0") or "0"
                    maximum_length = str(max_bytes)
                    if len(normalized_length) > len(maximum_length) or (
                        len(normalized_length) == len(maximum_length)
                        and normalized_length > maximum_length
                    ):
                        raise OfficialSourceCollectionError(
                            "official source Content-Length exceeds size limit"
                        )
                    declared_length = int(normalized_length)
                chunks = []
                total = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    if type(chunk) is not bytes:
                        raise OfficialSourceCollectionError(
                            "official source response is not immutable bytes"
                        )
                    total += len(chunk)
                    if total > max_bytes:
                        raise OfficialSourceCollectionError(
                            "official source response exceeds size limit"
                        )
                    chunks.append(chunk)
                if declared_length is not None and total != declared_length:
                    raise OfficialSourceCollectionError(
                        "official source response length does not match its header"
                    )
                if total == 0:
                    raise OfficialSourceCollectionError(
                        "official source response must be nonempty"
                    )
        except requests.RequestException as exc:
            raise OfficialSourceCollectionError(
                "official source HTTPS request failed"
            ) from exc
        return b"".join(chunks)


@dataclass(frozen=True)
class OfficialSourceCollection:
    """Two source assets and the instant at which collection completed."""

    sources: tuple[RawSource, RawSource]
    completed_at: datetime


def _is_canonical_official_url(url: str) -> bool:
    if url == WCLC_URL:
        return True
    if not url.startswith(_LOTO_QUEBEC_URL_PREFIX):
        return False
    raw_date = url.removeprefix(_LOTO_QUEBEC_URL_PREFIX)
    try:
        parsed_date = date.fromisoformat(raw_date)
    except ValueError:
        return False
    return (
        raw_date == parsed_date.isoformat()
        and len(raw_date) == 10
        and parsed_date.weekday() in (2, 5)
    )


def _clock_instant(clock: Callable[[], datetime]) -> datetime:
    try:
        value = clock()
        if type(value) is not datetime or value.tzinfo is None:
            raise ValueError("clock value is not aware")
        if value.utcoffset() is None or value.microsecond != 0:
            raise ValueError("clock value lacks exact precision")
        return value.astimezone(UTC)
    except Exception as exc:
        raise OfficialSourceCollectionError(
            "source collection clock must return a UTC whole-second instant"
        ) from exc


def collect_official_sources(
    target_draw_date: date,
    *,
    http_client: OfficialSourceHttpClient,
    clock: Callable[[], datetime],
) -> OfficialSourceCollection:
    """Collect WCLC and Loto-Québec bytes without writing repository state."""

    if type(target_draw_date) is not date or target_draw_date.weekday() not in (2, 5):
        raise OfficialSourceCollectionError(
            "target date must be a Wednesday or Saturday scheduled draw"
        )
    specifications = (
        ("wclc", WCLC_URL),
        (
            "loto_quebec",
            LOTO_QUEBEC_URL_TEMPLATE.format(draw_date=target_draw_date.isoformat()),
        ),
    )
    sources = []
    previous_instant: datetime | None = None
    for authority, url in specifications:
        try:
            raw = http_client.fetch(url, max_bytes=MAX_SOURCE_BYTES)
        except Exception as exc:
            raise OfficialSourceCollectionError(
                f"{authority} official source retrieval failed"
            ) from exc
        if type(raw) is not bytes or not raw:
            raise OfficialSourceCollectionError(
                "source bytes must be nonempty immutable bytes"
            )
        if len(raw) > MAX_SOURCE_BYTES:
            raise OfficialSourceCollectionError("source response exceeds size limit")
        retrieved_at = _clock_instant(clock)
        if retrieved_at.astimezone(_DRAW_TIME_ZONE).date() <= target_draw_date:
            raise OfficialSourceCollectionError(
                "source receipt must be strictly after target draw date"
            )
        if previous_instant is not None and retrieved_at < previous_instant:
            raise OfficialSourceCollectionError(
                "source collection clock must be monotonic"
            )
        previous_instant = retrieved_at
        sources.append(
            RawSource(
                authority=authority,
                url=url,
                retrieved_at=retrieved_at,
                raw=raw,
            )
        )
    if sources[0].raw == sources[1].raw:
        raise OfficialSourceCollectionError(
            "independent official sources must have distinct bytes"
        )
    return OfficialSourceCollection(
        sources=(sources[0], sources[1]),
        completed_at=sources[-1].retrieved_at,
    )
