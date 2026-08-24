from __future__ import annotations

import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import requests

from lotto649.history_publication import (
    RawSource,
    prepare_history_publication,
)
from lotto649.official_source_collection import (
    LOTO_QUEBEC_URL_TEMPLATE,
    OfficialSourceCollection,
    OfficialSourceCollectionError,
    RequestsOfficialSourceHttpClient,
    collect_official_sources,
)
from lotto649.operational_history import load_published_history


ROOT = Path(__file__).resolve().parents[1]


WCLC_URL = "https://www.wclc.com/winning-numbers/lotto-649-extra.htm"
LOTO_QUEBEC_URL = (
    "https://loteries.lotoquebec.com/en/lotteries/lotto-6-49-resultats?date=2026-08-26"
)


def _valid_wclc_html(draw_date: date) -> bytes:
    weekdays = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )
    months = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    display_date = (
        f"{weekdays[draw_date.weekday()]}, {months[draw_date.month - 1]} "
        f"{draw_date.day}, {draw_date.year}"
    )
    return (
        b"<!doctype html><html><body>"
        + display_date.encode("ascii")
        + b" CLASSIC DRAW 02 07 18 23 35 49 Bonus 11</body></html>"
    )


def _valid_loto_quebec_html(draw_date: date) -> bytes:
    return (
        b"<!doctype html><html><body>"
        + f'<span id="dateAffichee">{draw_date.isoformat()}</span>'.encode()
        + b""
        b'<div class="lqZoneProduit principal lotto-6-49">'
        b'<div class="numeros tirageClassique">'
        b'<span class="num">02</span><span class="num">07</span>'
        b'<span class="num">18</span><span class="num">23</span>'
        b'<span class="num">35</span><span class="num">49</span>'
        b'<span class="num complementaire">11</span>'
        b"</div></div></body></html>"
    )


class _StaticHttpClient:
    def __init__(self, responses: dict[str, bytes]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, int]] = []

    def fetch(self, url: str, *, max_bytes: int) -> bytes:
        self.requests.append((url, max_bytes))
        return self._responses[url]


class _StreamingResponse:
    def __init__(
        self,
        *,
        url: str,
        status_code: int = 200,
        content_type: str = "text/html; charset=UTF-8",
        chunks: tuple[bytes, ...] = (b"official ", b"html"),
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(sum(len(chunk) for chunk in chunks)),
        }
        self._chunks = chunks

    def __enter__(self) -> _StreamingResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def iter_content(self, *, chunk_size: int) -> tuple[bytes, ...]:
        assert chunk_size == 64 * 1024
        return self._chunks


def test_collect_returns_two_exact_immutable_official_assets() -> None:
    instants = iter(
        (
            datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC),
            datetime(2026, 8, 27, 12, 0, 1, tzinfo=UTC),
        )
    )
    client = _StaticHttpClient(
        {
            WCLC_URL: b"wclc official html",
            LOTO_QUEBEC_URL: b"loto-quebec official html",
        }
    )

    collected = collect_official_sources(
        date(2026, 8, 26),
        http_client=client,
        clock=lambda: next(instants),
    )

    assert collected == OfficialSourceCollection(
        sources=(
            RawSource(
                authority="wclc",
                url=WCLC_URL,
                retrieved_at=datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC),
                raw=b"wclc official html",
            ),
            RawSource(
                authority="loto_quebec",
                url=LOTO_QUEBEC_URL,
                retrieved_at=datetime(2026, 8, 27, 12, 0, 1, tzinfo=UTC),
                raw=b"loto-quebec official html",
            ),
        ),
        completed_at=datetime(2026, 8, 27, 12, 0, 1, tzinfo=UTC),
    )
    assert client.requests == [
        (WCLC_URL, 2 * 1024 * 1024),
        (LOTO_QUEBEC_URL, 2 * 1024 * 1024),
    ]


def test_collected_assets_feed_the_offline_publication_seam(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(repository)],
        check=True,
        capture_output=True,
    )
    base_commit = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    base_history = load_published_history(repository, base_commit)
    target_draw_date = base_history.draws[-1].draw_date + timedelta(
        days=3 if base_history.draws[-1].draw_date.weekday() == 2 else 4
    )
    receipt_date = target_draw_date + timedelta(days=1)
    instants = iter(
        (
            datetime.combine(receipt_date, datetime.min.time(), UTC).replace(hour=12),
            datetime.combine(receipt_date, datetime.min.time(), UTC).replace(
                hour=12, second=1
            ),
        )
    )
    collected = collect_official_sources(
        target_draw_date,
        http_client=_StaticHttpClient(
            {
                WCLC_URL: _valid_wclc_html(target_draw_date),
                LOTO_QUEBEC_URL_TEMPLATE.format(
                    draw_date=target_draw_date.isoformat()
                ): _valid_loto_quebec_html(target_draw_date),
            }
        ),
        clock=lambda: next(instants),
    )

    prepared = prepare_history_publication(
        repository,
        expected_base_commit=base_commit,
        sources=collected.sources,
        created_at=collected.completed_at,
    )
    published = load_published_history(repository, prepared.publication_commit)

    assert prepared.target_draw_date == target_draw_date
    assert len(published.draws) == len(base_history.draws) + 1
    assert published.draws[-1].draw_date == target_draw_date


def test_collect_rejects_an_invalid_source_body() -> None:
    client = _StaticHttpClient(
        {
            WCLC_URL: b"",
            LOTO_QUEBEC_URL: b"loto-quebec official html",
        }
    )

    with pytest.raises(OfficialSourceCollectionError, match="nonempty immutable"):
        collect_official_sources(
            date(2026, 8, 26),
            http_client=client,
            clock=lambda: datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
        )

    assert client.requests == [(WCLC_URL, 2 * 1024 * 1024)]


def test_collect_rejects_an_off_schedule_target_before_network_access() -> None:
    client = _StaticHttpClient({})

    with pytest.raises(OfficialSourceCollectionError, match="scheduled draw"):
        collect_official_sources(
            date(2026, 8, 27),
            http_client=client,
            clock=lambda: datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
        )

    assert client.requests == []


def test_collect_rejects_a_receipt_not_strictly_after_the_draw_date() -> None:
    client = _StaticHttpClient(
        {
            WCLC_URL: b"wclc official html",
            LOTO_QUEBEC_URL: b"loto-quebec official html",
        }
    )

    with pytest.raises(OfficialSourceCollectionError, match="after target draw"):
        collect_official_sources(
            date(2026, 8, 26),
            http_client=client,
            clock=lambda: datetime(2026, 8, 26, 23, 59, 59, tzinfo=UTC),
        )

    assert client.requests == [(WCLC_URL, 2 * 1024 * 1024)]


def test_collect_rejects_next_utc_day_while_toronto_is_still_on_draw_day() -> None:
    client = _StaticHttpClient(
        {
            WCLC_URL: b"wclc official html",
            LOTO_QUEBEC_URL: b"loto-quebec official html",
        }
    )

    with pytest.raises(OfficialSourceCollectionError, match="after target draw"):
        collect_official_sources(
            date(2026, 8, 26),
            http_client=client,
            clock=lambda: datetime(2026, 8, 27, 0, 0, tzinfo=UTC),
        )

    assert client.requests == [(WCLC_URL, 2 * 1024 * 1024)]


def test_collect_rejects_a_naive_clock_value() -> None:
    client = _StaticHttpClient(
        {
            WCLC_URL: b"wclc official html",
            LOTO_QUEBEC_URL: b"loto-quebec official html",
        }
    )

    with pytest.raises(OfficialSourceCollectionError, match="UTC whole-second"):
        collect_official_sources(
            date(2026, 8, 26),
            http_client=client,
            clock=lambda: datetime(2026, 8, 27, 12, 0),
        )

    assert client.requests == [(WCLC_URL, 2 * 1024 * 1024)]


def test_collect_wraps_a_clock_failure_as_a_typed_collection_error() -> None:
    client = _StaticHttpClient(
        {
            WCLC_URL: b"wclc official html",
            LOTO_QUEBEC_URL: b"loto-quebec official html",
        }
    )

    def failed_clock() -> datetime:
        raise RuntimeError("host clock unavailable")

    with pytest.raises(OfficialSourceCollectionError, match="clock"):
        collect_official_sources(
            date(2026, 8, 26),
            http_client=client,
            clock=failed_clock,
        )

    assert client.requests == [(WCLC_URL, 2 * 1024 * 1024)]


def test_collect_rejects_a_clock_that_moves_backwards() -> None:
    instants = iter(
        (
            datetime(2026, 8, 27, 12, 0, 1, tzinfo=UTC),
            datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC),
        )
    )
    client = _StaticHttpClient(
        {
            WCLC_URL: b"wclc official html",
            LOTO_QUEBEC_URL: b"loto-quebec official html",
        }
    )

    with pytest.raises(OfficialSourceCollectionError, match="monotonic"):
        collect_official_sources(
            date(2026, 8, 26),
            http_client=client,
            clock=lambda: next(instants),
        )

    assert client.requests == [
        (WCLC_URL, 2 * 1024 * 1024),
        (LOTO_QUEBEC_URL, 2 * 1024 * 1024),
    ]


def test_collect_rejects_identical_bytes_from_the_two_authorities() -> None:
    instants = iter(
        (
            datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC),
            datetime(2026, 8, 27, 12, 0, 1, tzinfo=UTC),
        )
    )
    client = _StaticHttpClient(
        {
            WCLC_URL: b"same asset",
            LOTO_QUEBEC_URL: b"same asset",
        }
    )

    with pytest.raises(OfficialSourceCollectionError, match="distinct bytes"):
        collect_official_sources(
            date(2026, 8, 26),
            http_client=client,
            clock=lambda: next(instants),
        )


def test_requests_client_returns_the_exact_bounded_html_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_get(url: str, **kwargs: object) -> _StreamingResponse:
        observed.update({"url": url, **kwargs})
        return _StreamingResponse(url=url)

    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        fake_get,
    )

    raw = RequestsOfficialSourceHttpClient().fetch(
        WCLC_URL,
        max_bytes=2 * 1024 * 1024,
    )

    assert raw == b"official html"
    assert observed == {
        "url": WCLC_URL,
        "allow_redirects": False,
        "headers": {
            "Accept-Encoding": "identity",
            "User-Agent": "lotto649-verified-history/1",
        },
        "stream": True,
        "timeout": (10, 30),
    }


def test_requests_client_accepts_the_exact_loto_quebec_draw_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda url, **_kwargs: _StreamingResponse(url=url),
    )

    raw = RequestsOfficialSourceHttpClient().fetch(
        LOTO_QUEBEC_URL,
        max_bytes=2 * 1024 * 1024,
    )

    assert raw == b"official html"


def test_requests_client_rejects_redirects_and_non_success_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: _StreamingResponse(
            url=WCLC_URL,
            status_code=302,
        ),
    )

    with pytest.raises(OfficialSourceCollectionError, match="HTTP 200"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


def test_requests_client_rejects_a_response_from_another_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: _StreamingResponse(
            url="https://example.invalid/redirected",
        ),
    )

    with pytest.raises(OfficialSourceCollectionError, match="exact requested URL"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


def test_requests_client_rejects_a_non_html_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: _StreamingResponse(
            url=WCLC_URL,
            content_type="application/octet-stream",
        ),
    )

    with pytest.raises(OfficialSourceCollectionError, match="text/html"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


def test_requests_client_rejects_a_content_encoded_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _StreamingResponse(url=WCLC_URL)
    response.headers["Content-Encoding"] = "gzip"
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(OfficialSourceCollectionError, match="Content-Encoding"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


def test_requests_client_rejects_an_oversized_declared_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _StreamingResponse(url=WCLC_URL)
    response.headers["Content-Length"] = str(2 * 1024 * 1024 + 1)
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(OfficialSourceCollectionError, match="size limit"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


@pytest.mark.parametrize(
    "content_length",
    ["not-a-number", "9" * 5_000],
)
def test_requests_client_rejects_a_malformed_content_length(
    monkeypatch: pytest.MonkeyPatch,
    content_length: str,
) -> None:
    response = _StreamingResponse(url=WCLC_URL)
    response.headers["Content-Length"] = content_length
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(OfficialSourceCollectionError, match="Content-Length"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


def test_requests_client_rejects_a_stream_that_exceeds_its_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _StreamingResponse(
        url=WCLC_URL,
        chunks=(b"1234", b"5"),
    )
    response.headers.pop("Content-Length")
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(OfficialSourceCollectionError, match="size limit"):
        RequestsOfficialSourceHttpClient().fetch(WCLC_URL, max_bytes=4)


def test_requests_client_rejects_a_length_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _StreamingResponse(url=WCLC_URL)
    response.headers["Content-Length"] = "99"
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(OfficialSourceCollectionError, match="does not match"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


def test_requests_client_wraps_a_request_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_get(*_args: object, **_kwargs: object) -> object:
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        failed_get,
    )

    with pytest.raises(OfficialSourceCollectionError, match="HTTPS request failed"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


def test_requests_client_rejects_a_non_bytes_stream_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _StreamingResponse(url=WCLC_URL)
    response.headers.pop("Content-Length")
    response._chunks = ("not bytes",)  # type: ignore[assignment]
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(OfficialSourceCollectionError, match="immutable bytes"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


def test_requests_client_rejects_an_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        lambda *_args, **_kwargs: _StreamingResponse(
            url=WCLC_URL,
            chunks=(),
        ),
    )

    with pytest.raises(OfficialSourceCollectionError, match="nonempty"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=2 * 1024 * 1024,
        )


def test_requests_client_rejects_an_unapproved_url_before_network_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_get(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("network should be unreachable")

    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        unexpected_get,
    )

    with pytest.raises(OfficialSourceCollectionError, match="canonical official URL"):
        RequestsOfficialSourceHttpClient().fetch(
            "https://example.invalid/lotto",
            max_bytes=2 * 1024 * 1024,
        )


@pytest.mark.parametrize("max_bytes", [True, 0, 2 * 1024 * 1024 + 1])
def test_requests_client_rejects_an_invalid_limit_before_network_access(
    monkeypatch: pytest.MonkeyPatch,
    max_bytes: object,
) -> None:
    def unexpected_get(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("network should be unreachable")

    monkeypatch.setattr(
        "lotto649.official_source_collection.requests.get",
        unexpected_get,
    )

    with pytest.raises(OfficialSourceCollectionError, match="size limit"):
        RequestsOfficialSourceHttpClient().fetch(
            WCLC_URL,
            max_bytes=max_bytes,  # type: ignore[arg-type]
        )
