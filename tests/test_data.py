from datetime import date, timedelta
import pytest

from lotto649.data import parse_wclc_recent_html, parse_lottonet_year_html, merge_draws
from lotto649.domain import Draw


def test_parse_wclc_recent_draw():
    html = """
    <html><body>
      Wednesday, August 12, 2026
      CLASSIC DRAW 6 13 28 34 45 48 Bonus 46
    </body></html>
    """
    draws = parse_wclc_recent_html(html)
    assert len(draws) == 1
    assert draws[0].numbers == (6, 13, 28, 34, 45, 48)
    assert draws[0].bonus == 46


def test_parse_lottonet_bridge_uses_last_seven_before_bonus():
    # The production parser deliberately refuses implausibly tiny annual pages,
    # so the fixture contains ten draw blocks while we assert the first one.
    start = date(2024, 12, 1)
    blocks = []
    for i in range(10):
        d = start + timedelta(days=i)
        blocks.append(
            f"<h2>{d.strftime('%A %B')} {d.day}th {d.year}</h2>"
            "<p>Jackpot CA$5,000,000</p>"
            "<ul><li>8</li><li>16</li><li>18</li><li>23</li><li>34</li><li>36</li><li>12</li></ul>"
            "<p>Bonus</p>"
        )
    draws = parse_lottonet_year_html("<html><body>" + "".join(blocks) + "</body></html>")
    assert len(draws) == 10
    assert draws[0].draw_date == date(2024, 12, 1)
    assert draws[0].numbers == (8, 16, 18, 23, 34, 36)
    assert draws[0].bonus == 12


def test_merge_refuses_conflicting_sources():
    a = Draw(date(2026, 8, 12), (6, 13, 28, 34, 45, 48), 46)
    b = Draw(date(2026, 8, 12), (1, 2, 3, 4, 5, 6), 7)
    with pytest.raises(RuntimeError):
        merge_draws([a], [b])
