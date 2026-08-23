from datetime import date

import pytest

from lotto649.domain import Draw
from lotto649.official_history import (
    canonical_official_rows_sha256,
    canonical_official_text_rows_sha256,
    expected_lotto649_draw_dates,
    parse_lotoquebec_annual_html,
    parse_lotoquebec_detail_html,
    validate_complete_official_history,
)


def test_parse_lotoquebec_annual_html_reads_one_official_row():
    html = """
    <table>
      <tr><th class="date">Date</th><th>Numéros gagnants</th></tr>
      <tr>
        <td class="date">2024-12-28</td>
        <td>
          <div>Le tirage classique</div>
          <div class="numerosGagnants principal">
            <span>08</span><span>16</span><span>18</span>
            <span>23</span><span>34</span><span>36</span>
            (<span>12</span>)
          </div>
        </td>
      </tr>
    </table>
    """

    assert parse_lotoquebec_annual_html(html, 2024) == [
        Draw(date(2024, 12, 28), (8, 16, 18, 23, 34, 36), 12)
    ]


def test_parse_lotoquebec_annual_html_accepts_official_malformed_bonus_span():
    html = """
      <table><tr><td class="date">2025-12-31</td><td>
        <div class="numerosGagnants principal">
          <span>01</span><span>06</span><span>10</span><span>21</span>
          <span>39</span><span>40</span>&nbsp;(<span>28<span>)</span></span>
        </div>
      </td></tr></table>
    """

    assert parse_lotoquebec_annual_html(html, 2025) == [
        Draw(date(2025, 12, 31), (1, 6, 10, 21, 39, 40), 28)
    ]


def test_parse_lotoquebec_annual_html_ignores_2001_bonus_prize_combinations():
    html = """
      <table><tr><td class="date">2001-10-27</td><td>
        <div class="numerosGangnants principal">
          <span>18</span><span>21</span><span>25</span><span>26</span>
          <span>32</span><span>48</span>(<span>38</span>)
        </div>
        <div class="titre lotBoni">Bonus Prizes</div>
        <div class="numerosGangnants principal">
          <span>01</span><span>03</span><span>07</span>
          <span>14</span><span>16</span><span>32</span>
        </div>
        <div class="numerosGangnants principal">
          <span>10</span><span>12</span><span>16</span>
          <span>26</span><span>41</span><span>42</span>
        </div>
      </td></tr></table>
    """

    assert parse_lotoquebec_annual_html(html, 2001) == [
        Draw(date(2001, 10, 27), (18, 21, 25, 26, 32, 48), 38)
    ]


def test_parse_lotoquebec_annual_html_returns_every_row_in_chronological_order():
    html = """
      <table>
        <tr><td class="date">2020-01-04</td><td>
          <div class="numerosGagnants principal">
            <span>08</span><span>09</span><span>10</span><span>11</span>
            <span>12</span><span>13</span>(<span>14</span>)
          </div>
        </td></tr>
        <tr><td class="date">2020-01-01</td><td>
          <div class="numerosGangnants principal">
            <span>01</span><span>02</span><span>03</span><span>04</span>
            <span>05</span><span>06</span>(<span>07</span>)
          </div>
        </td></tr>
      </table>
    """

    assert parse_lotoquebec_annual_html(html, 2020) == [
        Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7),
        Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14),
    ]


def test_parse_lotoquebec_annual_html_rejects_duplicate_dates():
    row = """
      <tr>
        <td class="date">2020-01-01</td>
        <td><div class="numerosGangnants principal">
          <span>01</span><span>02</span><span>03</span>
          <span>04</span><span>05</span><span>06</span>(<span>07</span>)
        </div></td>
      </tr>
    """

    with pytest.raises(RuntimeError, match="Duplicate official history date"):
        parse_lotoquebec_annual_html(f"<table>{row}{row}</table>", 2020)


def test_parse_lotoquebec_annual_html_rejects_conflicting_rows():
    first = """
      <tr><td class="date">2020-01-01</td><td>
        <div class="numerosGangnants principal">
          <span>01</span><span>02</span><span>03</span><span>04</span>
          <span>05</span><span>06</span>(<span>07</span>)
        </div>
      </td></tr>
    """
    conflicting = """
      <tr><td class="date">2020-01-01</td><td>
        <div class="numerosGagnants principal">
          <span>08</span><span>09</span><span>10</span><span>11</span>
          <span>12</span><span>13</span>(<span>14</span>)
        </div>
      </td></tr>
    """

    with pytest.raises(RuntimeError, match="Conflicting official history rows"):
        parse_lotoquebec_annual_html(f"<table>{first}{conflicting}</table>", 2020)


def test_parse_lotoquebec_annual_html_rejects_an_empty_widget():
    with pytest.raises(RuntimeError, match="contains no official draw rows"):
        parse_lotoquebec_annual_html(
            "<table><tr><th class='date'>Date</th></tr></table>", 2020
        )


def test_parse_lotoquebec_annual_html_rejects_ambiguous_classic_draw_blocks():
    principal = """
      <div class="numerosGagnants principal">
        <span>01</span><span>02</span><span>03</span><span>04</span>
        <span>05</span><span>06</span>(<span>07</span>)
      </div>
    """
    html = f"""
      <table><tr><td class="date">2020-01-01</td><td>
        {principal}{principal}
      </td></tr></table>
    """

    with pytest.raises(RuntimeError, match="classic draw blocks"):
        parse_lotoquebec_annual_html(html, 2020)


def test_parse_lotoquebec_annual_html_rejects_a_nonnumeric_ball():
    html = """
      <table><tr><td class="date">2020-01-01</td><td>
        <div class="numerosGagnants principal">
          <span>01</span><span>02</span><span>03</span><span>04</span>
          <span>05</span><span>XX</span>(<span>07</span>)
        </div>
      </td></tr></table>
    """

    with pytest.raises(RuntimeError, match="malformed ball value"):
        parse_lotoquebec_annual_html(html, 2020)


def test_parse_lotoquebec_annual_html_rejects_an_invalid_649_row():
    html = """
      <table><tr><td class="date">2020-01-01</td><td>
        <div class="numerosGagnants principal">
          <span>01</span><span>02</span><span>03</span><span>04</span>
          <span>05</span><span>06</span>(<span>06</span>)
        </div>
      </td></tr></table>
    """

    with pytest.raises(RuntimeError, match="invalid 6/49 values"):
        parse_lotoquebec_annual_html(html, 2020)


def test_parse_lotoquebec_annual_html_rejects_a_malformed_date():
    html = """
      <table><tr><td class="date">2020-02-30</td><td>
        <div class="numerosGagnants principal">
          <span>01</span><span>02</span><span>03</span><span>04</span>
          <span>05</span><span>06</span>(<span>07</span>)
        </div>
      </td></tr></table>
    """

    with pytest.raises(RuntimeError, match="malformed draw date"):
        parse_lotoquebec_annual_html(html, 2020)


def test_parse_lotoquebec_annual_html_rejects_a_row_from_another_year():
    html = """
      <table><tr><td class="date">2019-12-28</td><td>
        <div class="numerosGagnants principal">
          <span>02</span><span>04</span><span>12</span><span>18</span>
          <span>29</span><span>41</span>(<span>30</span>)
        </div>
      </td></tr></table>
    """

    with pytest.raises(RuntimeError, match="outside expected year 2020"):
        parse_lotoquebec_annual_html(html, 2020)


def test_parse_lotoquebec_annual_html_rejects_ambiguous_date_cells():
    html = """
      <table><tr>
        <td class="date">2020-01-01</td><td class="date">2020-01-04</td>
        <td><div class="numerosGagnants principal">
          <span>01</span><span>02</span><span>03</span><span>04</span>
          <span>05</span><span>06</span>(<span>07</span>)
        </div></td>
      </tr></table>
    """

    with pytest.raises(RuntimeError, match="date cells, expected 1"):
        parse_lotoquebec_annual_html(html, 2020)


def test_parse_lotoquebec_detail_html_reads_the_scoped_classic_draw():
    html = """
      <div id="dateAffichee">2026-01-21</div>
      <div class="lqZoneProduits">
        <div class="lqZoneProduit principal lotto-6-49">
          <div class="lqZoneResultatsProduit">
            <div class="numeros tirageClassique">
              <span class="num">04</span><span class="num-sep">-</span>
              <span class="num">13</span><span class="num-sep">-</span>
              <span class="num">21</span><span class="num-sep">-</span>
              <span class="num">27</span><span class="num-sep">-</span>
              <span class="num">34</span><span class="num-sep">-</span>
              <span class="num">39</span>
              <span class="libelleComplementaire">Bonus&nbsp;(B):</span>
              <span class="parentheses">(</span>
              <span class="num complementaire">36</span>
              <span class="parentheses">)</span>
            </div>
          </div>
        </div>
        <div class="lqZoneProduit secondaire quebec-49">
          <div class="numeros tirageClassique">
            <span class="num">01</span><span class="num">09</span>
            <span class="num">11</span><span class="num">18</span>
            <span class="num">25</span><span class="num">45</span>
            <span class="num complementaire">33</span>
          </div>
        </div>
      </div>
    """

    assert parse_lotoquebec_detail_html(html, date(2026, 1, 21)) == Draw(
        date(2026, 1, 21), (4, 13, 21, 27, 34, 39), 36
    )


def test_parse_lotoquebec_detail_html_rejects_multiple_displayed_dates():
    html = """
      <div id="dateAffichee">2026-01-21</div>
      <div id="dateAffichee">2026-01-24</div>
      <div class="lqZoneProduit principal lotto-6-49">
        <div class="numeros tirageClassique">
          <span class="num">04</span><span class="num">13</span>
          <span class="num">21</span><span class="num">27</span>
          <span class="num">34</span><span class="num">39</span>
          <span class="num complementaire">36</span>
        </div>
      </div>
    """

    with pytest.raises(RuntimeError, match="displayed dates, expected 1"):
        parse_lotoquebec_detail_html(html, date(2026, 1, 21))


def test_parse_lotoquebec_detail_html_rejects_a_different_displayed_date():
    html = """
      <div id="dateAffichee">2026-01-24</div>
      <div class="lqZoneProduit principal lotto-6-49">
        <div class="numeros tirageClassique">
          <span class="num">04</span><span class="num">13</span>
          <span class="num">21</span><span class="num">27</span>
          <span class="num">34</span><span class="num">39</span>
          <span class="num complementaire">36</span>
        </div>
      </div>
    """

    with pytest.raises(RuntimeError, match="does not match 2026-01-21"):
        parse_lotoquebec_detail_html(html, date(2026, 1, 21))


def test_parse_lotoquebec_detail_html_rejects_multiple_649_classic_blocks():
    classic = """
      <div class="numeros tirageClassique">
        <span class="num">04</span><span class="num">13</span>
        <span class="num">21</span><span class="num">27</span>
        <span class="num">34</span><span class="num">39</span>
        <span class="num complementaire">36</span>
      </div>
    """
    html = f"""
      <div id="dateAffichee">2026-01-21</div>
      <div class="lqZoneProduit principal lotto-6-49">{classic}{classic}</div>
    """

    with pytest.raises(RuntimeError, match="classic blocks, expected 1"):
        parse_lotoquebec_detail_html(html, date(2026, 1, 21))


def test_parse_lotoquebec_detail_html_rejects_a_missing_649_classic_block():
    html = """
      <div id="dateAffichee">2026-01-21</div>
      <div class="lqZoneProduit secondaire quebec-49">
        <div class="numeros tirageClassique">
          <span class="num">01</span><span class="num">09</span>
          <span class="num">11</span><span class="num">18</span>
          <span class="num">25</span><span class="num">45</span>
          <span class="num complementaire">33</span>
        </div>
      </div>
    """

    with pytest.raises(RuntimeError, match="0 6/49 classic blocks, expected 1"):
        parse_lotoquebec_detail_html(html, date(2026, 1, 21))


def test_parse_lotoquebec_detail_html_requires_exactly_six_plus_one():
    html = """
      <div id="dateAffichee">2026-01-21</div>
      <div class="lqZoneProduit principal lotto-6-49">
        <div class="numeros tirageClassique">
          <span class="num">04</span><span class="num">13</span>
          <span class="num">21</span><span class="num">27</span>
          <span class="num">34</span><span class="num">39</span>
          <span class="num complementaire">36</span>
          <span class="num complementaire">41</span>
        </div>
      </div>
    """

    with pytest.raises(RuntimeError, match="6 main numbers and 1 bonus"):
        parse_lotoquebec_detail_html(html, date(2026, 1, 21))


def test_parse_lotoquebec_detail_html_rejects_a_nonnumeric_ball():
    html = """
      <div id="dateAffichee">2026-01-21</div>
      <div class="lqZoneProduit principal lotto-6-49">
        <div class="numeros tirageClassique">
          <span class="num">04</span><span class="num">13</span>
          <span class="num">21</span><span class="num">XX</span>
          <span class="num">34</span><span class="num">39</span>
          <span class="num complementaire">36</span>
        </div>
      </div>
    """

    with pytest.raises(RuntimeError, match="malformed ball value"):
        parse_lotoquebec_detail_html(html, date(2026, 1, 21))


@pytest.mark.parametrize(
    ("main", "bonus"),
    [
        ((4, 4, 21, 27, 34, 39), 36),
        ((4, 13, 21, 27, 34, 39), 50),
    ],
    ids=("duplicate", "out-of-range"),
)
def test_parse_lotoquebec_detail_html_rejects_invalid_649_values(main, bonus):
    main_html = "".join(f'<span class="num">{value:02d}</span>' for value in main)
    html = f"""
      <div id="dateAffichee">2026-01-21</div>
      <div class="lqZoneProduit principal lotto-6-49">
        <div class="numeros tirageClassique">
          {main_html}<span class="num complementaire">{bonus:02d}</span>
        </div>
      </div>
    """

    with pytest.raises(RuntimeError, match="invalid 6/49 values"):
        parse_lotoquebec_detail_html(html, date(2026, 1, 21))


def test_expected_lotto649_draw_dates_freezes_both_schedule_eras():
    dates = expected_lotto649_draw_dates(date(2026, 8, 15))

    assert len(dates) == 4442
    assert dates[:2] == [date(1982, 6, 12), date(1982, 6, 19)]
    transition = dates.index(date(1985, 9, 7))
    assert dates[transition : transition + 3] == [
        date(1985, 9, 7),
        date(1985, 9, 11),
        date(1985, 9, 14),
    ]
    assert dates[-1] == date(2026, 8, 15)

    diagnostic = [
        draw_date
        for draw_date in dates
        if date(2020, 1, 1) <= draw_date <= date(2025, 12, 31)
    ]
    assert len(diagnostic) == 627
    assert sum(draw_date <= date(2022, 12, 31) for draw_date in diagnostic) == 314
    assert sum(draw_date >= date(2023, 1, 1) for draw_date in diagnostic) == 313


def test_validate_complete_official_history_accepts_the_exact_date_set():
    draws = [
        Draw(date(1982, 6, 12), (1, 2, 3, 4, 5, 6), 7),
        Draw(date(1982, 6, 19), (8, 9, 10, 11, 12, 13), 14),
    ]

    assert validate_complete_official_history(draws, date(1982, 6, 19)) is None


@pytest.mark.parametrize(
    ("draws", "message"),
    [
        (
            [Draw(date(1982, 6, 12), (1, 2, 3, 4, 5, 6), 7)],
            "missing=1982-06-19; extra=none",
        ),
        (
            [
                Draw(date(1982, 6, 12), (1, 2, 3, 4, 5, 6), 7),
                Draw(date(1982, 6, 16), (8, 9, 10, 11, 12, 13), 14),
                Draw(date(1982, 6, 19), (15, 16, 17, 18, 19, 20), 21),
            ],
            "missing=none; extra=1982-06-16",
        ),
    ],
    ids=("missing", "extra"),
)
def test_validate_complete_official_history_rejects_date_set_drift(draws, message):
    with pytest.raises(RuntimeError, match=message):
        validate_complete_official_history(draws, date(1982, 6, 19))


def test_validate_complete_official_history_requires_a_bonus_in_every_row():
    draws = [Draw(date(1982, 6, 12), (1, 2, 3, 4, 5, 6), None)]

    with pytest.raises(RuntimeError, match="has no bonus number"):
        validate_complete_official_history(draws, date(1982, 6, 12))


def test_validate_complete_official_history_rejects_duplicate_dates():
    row = Draw(date(1982, 6, 12), (1, 2, 3, 4, 5, 6), 7)

    with pytest.raises(RuntimeError, match="contains duplicate date"):
        validate_complete_official_history([row, row], date(1982, 6, 12))


def test_canonical_official_rows_sha256_has_a_frozen_order_independent_identity():
    later = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    earlier = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)

    assert canonical_official_rows_sha256([later, earlier]) == (
        "3ba186f94ca5ec146677a11201408ce9692b95f0330e3f2b644c139913ed974c"
    )


def test_canonical_official_rows_sha256_rejects_duplicate_dates():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)

    with pytest.raises(RuntimeError, match="duplicate date"):
        canonical_official_rows_sha256([row, row])


def test_canonical_official_rows_sha256_rejects_a_missing_bonus():
    row = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), None)

    with pytest.raises(RuntimeError, match="has no bonus number"):
        canonical_official_rows_sha256([row])


def test_canonical_official_text_rows_sha256_freezes_source_collection_lines():
    later = Draw(date(2020, 1, 4), (8, 9, 10, 11, 12, 13), 14)
    earlier = Draw(date(2020, 1, 1), (1, 2, 3, 4, 5, 6), 7)

    assert canonical_official_text_rows_sha256([later, earlier]) == (
        "c2b8f97e822acf87008dc0fde617bcd5ade9be6d9aaae7c43e30bf71c72d9098"
    )
